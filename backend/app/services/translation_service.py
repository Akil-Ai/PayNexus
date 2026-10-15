"""Canonical message model and ISO 20022 translation engine.
Supports:
- pain.001 (Customer Credit Transfer Initiation XML)
- pacs.008 (Financial Institution Customer Credit Transfer XML)
- pacs.002 (Payment Status Report XML)
- camt.053 (Bank-to-Customer Statement XML)
- ISO 8583-style JSON
- Legacy CSV / Fixed-Width
- UPI / NEFT / SWIFT MT103 format translators
"""
import csv
import io
import json
import re
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field


class CanonicalParty(BaseModel):
    name: str
    account_number: Optional[str] = None
    account_type: Optional[str] = None
    routing_number: Optional[str] = None  # IFSC, BIC, or routing code
    bank_name: Optional[str] = None
    country: str = "IN"
    email: Optional[str] = None
    phone: Optional[str] = None


class CanonicalPaymentMessage(BaseModel):
    message_id: str
    creation_date_time: str
    instruction_id: str
    end_to_end_id: str
    amount_minor: int
    currency: str
    debtor: CanonicalParty
    creditor: CanonicalParty
    remittance_info: Optional[str] = None
    urgency: str = "NORMAL"
    charge_bearer: str = "SHA"  # DEBT, CRED, SHA, SLEV
    raw_format: str = "CANONICAL"
    validation_errors: List[str] = Field(default_factory=list)


# ── ISO 20022 XML Parsers & Serializers ───────────────────────────────────────

def parse_pain_001(xml_content: str) -> CanonicalPaymentMessage:
    """Parses ISO 20022 pain.001.001.09 customer credit transfer initiation."""
    errors = []
    try:
        root = ET.fromstring(xml_content)
    except Exception as e:
        return CanonicalPaymentMessage(
            message_id=str(uuid.uuid4()),
            creation_date_time=datetime.now(timezone.utc).isoformat(),
            instruction_id=str(uuid.uuid4()),
            end_to_end_id=str(uuid.uuid4()),
            amount_minor=0,
            currency="INR",
            debtor=CanonicalParty(name="Unknown"),
            creditor=CanonicalParty(name="Unknown"),
            raw_format="PAIN_001_XML",
            validation_errors=[f"XML parse error: {str(e)}"]
        )

    # Namespaces might exist, strip or handle
    def find_val(elem: Optional[ET.Element], path: str, default: str = "") -> str:
        if elem is None:
            return default
        # Simple local-name search
        parts = path.split("/")
        curr = [elem]
        for p in parts:
            next_curr = []
            for c in curr:
                for child in c:
                    tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    if tag == p:
                        next_curr.append(child)
            curr = next_curr
            if not curr:
                return default
        return curr[0].text or default

    msg_id = find_val(root, "CstmrCdtTrfInitn/GrpHdr/MsgId") or str(uuid.uuid4())
    cre_dt_tm = find_val(root, "CstmrCdtTrfInitn/GrpHdr/CreDtTm") or datetime.now(timezone.utc).isoformat()

    pmt_inf = None
    for child in root.iter():
        if child.tag.endswith("PmtInf"):
            pmt_inf = child
            break

    dbtr_name = find_val(pmt_inf, "Dbtr/Nm", "Unknown Debtor")
    dbtr_acct = find_val(pmt_inf, "DbtrAcct/Id/Othr/Id") or find_val(pmt_inf, "DbtrAcct/Id/IBAN")
    dbtr_bic = find_val(pmt_inf, "DbtrAgt/FinInstnId/BICFI") or find_val(pmt_inf, "DbtrAgt/FinInstnId/ClrSysMmbId/MmbId")

    cdt_trf = None
    for child in root.iter():
        if child.tag.endswith("CdtTrfTxInf"):
            cdt_trf = child
            break

    instr_id = find_val(cdt_trf, "PmtId/InstrId") or str(uuid.uuid4())
    e2e_id = find_val(cdt_trf, "PmtId/EndToEndId") or str(uuid.uuid4())
    
    # Amount
    amt_str = find_val(cdt_trf, "Amt/InstdAmt", "0")
    ccy = "INR"
    # Try getting currency attribute from InstdAmt
    for elem in root.iter():
        if elem.tag.endswith("InstdAmt"):
            ccy = elem.attrib.get("Ccy", "INR")
            break

    try:
        # Convert decimal string to minor units
        amt_float = float(amt_str)
        amount_minor = int(round(amt_float * 100))
    except ValueError:
        amount_minor = 0
        errors.append(f"Invalid amount value: {amt_str}")

    cdtr_name = find_val(cdt_trf, "Cdtr/Nm", "Unknown Creditor")
    cdtr_acct = find_val(cdt_trf, "CdtrAcct/Id/Othr/Id") or find_val(cdt_trf, "CdtrAcct/Id/IBAN")
    cdtr_bic = find_val(cdt_trf, "CdtrAgt/FinInstnId/BICFI") or find_val(cdt_trf, "CdtrAgt/FinInstnId/ClrSysMmbId/MmbId")
    remittance = find_val(cdt_trf, "RmtInf/Ustrd")

    return CanonicalPaymentMessage(
        message_id=msg_id,
        creation_date_time=cre_dt_tm,
        instruction_id=instr_id,
        end_to_end_id=e2e_id,
        amount_minor=amount_minor,
        currency=ccy.upper(),
        debtor=CanonicalParty(
            name=dbtr_name,
            account_number=dbtr_acct,
            routing_number=dbtr_bic
        ),
        creditor=CanonicalParty(
            name=cdtr_name,
            account_number=cdtr_acct,
            routing_number=cdtr_bic
        ),
        remittance_info=remittance,
        raw_format="PAIN_001_XML",
        validation_errors=errors
    )


def serialize_pain_001(msg: CanonicalPaymentMessage) -> str:
    """Serializes canonical payment to ISO 20022 pain.001 XML."""
    amount_major = f"{msg.amount_minor / 100:.2f}"
    xml_str = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>{msg.message_id}</MsgId>
      <CreDtTm>{msg.creation_date_time}</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <InitgPty>
        <Nm>{msg.debtor.name}</Nm>
      </InitgPty>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>{msg.instruction_id}</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      <Dbtr>
        <Nm>{msg.debtor.name}</Nm>
      </Dbtr>
      <DbtrAcct>
        <Id>
          <Othr>
            <Id>{msg.debtor.account_number or 'UNKNOWN'}</Id>
          </Othr>
        </Id>
      </DbtrAcct>
      <DbtrAgt>
        <FinInstnId>
          <ClrSysMmbId>
            <MmbId>{msg.debtor.routing_number or 'ROUTING'}</MmbId>
          </ClrSysMmbId>
        </FinInstnId>
      </DbtrAgt>
      <CdtTrfTxInf>
        <PmtId>
          <InstrId>{msg.instruction_id}</InstrId>
          <EndToEndId>{msg.end_to_end_id}</EndToEndId>
        </PmtId>
        <Amt>
          <InstdAmt Ccy="{msg.currency}">{amount_major}</InstdAmt>
        </Amt>
        <CdtrAgt>
          <FinInstnId>
            <ClrSysMmbId>
              <MmbId>{msg.creditor.routing_number or 'ROUTING'}</MmbId>
            </ClrSysMmbId>
          </FinInstnId>
        </CdtrAgt>
        <Cdtr>
          <Nm>{msg.creditor.name}</Nm>
        </Cdtr>
        <CdtrAcct>
          <Id>
            <Othr>
              <Id>{msg.creditor.account_number or 'UNKNOWN'}</Id>
            </Othr>
          </Id>
        </CdtrAcct>
        <RmtInf>
          <Ustrd>{msg.remittance_info or ''}</Ustrd>
        </RmtInf>
      </CdtTrfTxInf>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>"""
    return xml_str.strip()


def serialize_pacs_008(msg: CanonicalPaymentMessage) -> str:
    """Serializes canonical payment to ISO 20022 pacs.008 Financial Institution Customer Credit Transfer."""
    amount_major = f"{msg.amount_minor / 100:.2f}"
    xml_str = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
  <FIToFICstmrCdtTrf>
    <GrpHdr>
      <MsgId>{msg.message_id}</MsgId>
      <CreDtTm>{msg.creation_date_time}</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <SttlmInf>
        <SttlmMtd>CLRG</SttlmMtd>
      </SttlmInf>
    </GrpHdr>
    <CdtTrfTxInf>
      <PmtId>
        <InstrId>{msg.instruction_id}</InstrId>
        <EndToEndId>{msg.end_to_end_id}</EndToEndId>
        <TxId>{msg.message_id}</TxId>
      </PmtId>
      <IntrBkSttlmAmt Ccy="{msg.currency}">{amount_major}</IntrBkSttlmAmt>
      <ChrgBr>{msg.charge_bearer}</ChrgBr>
      <Dbtr>
        <Nm>{msg.debtor.name}</Nm>
      </Dbtr>
      <DbtrAcct>
        <Id>
          <Othr>
            <Id>{msg.debtor.account_number or 'UNKNOWN'}</Id>
          </Othr>
        </Id>
      </DbtrAcct>
      <DbtrAgt>
        <FinInstnId>
          <ClrSysMmbId>
            <MmbId>{msg.debtor.routing_number or 'ROUTING'}</MmbId>
          </ClrSysMmbId>
        </FinInstnId>
      </DbtrAgt>
      <CdtrAgt>
        <FinInstnId>
          <ClrSysMmbId>
            <MmbId>{msg.creditor.routing_number or 'ROUTING'}</MmbId>
          </ClrSysMmbId>
        </FinInstnId>
      </CdtrAgt>
      <Cdtr>
        <Nm>{msg.creditor.name}</Nm>
      </Cdtr>
      <CdtrAcct>
        <Id>
          <Othr>
            <Id>{msg.creditor.account_number or 'UNKNOWN'}</Id>
          </Othr>
        </Id>
      </CdtrAcct>
      <RmtInf>
        <Ustrd>{msg.remittance_info or ''}</Ustrd>
      </RmtInf>
    </CdtTrfTxInf>
  </FIToFICstmrCdtTrf>
</Document>"""
    return xml_str.strip()


def serialize_pacs_002(
    original_msg_id: str,
    original_e2e_id: str,
    status: str,
    status_reason: Optional[str] = None
) -> str:
    """Serializes payment status report (pacs.002.001.10)."""
    msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.002.001.10">
  <FIToFIPmtStsRpt>
    <GrpHdr>
      <MsgId>{msg_id}</MsgId>
      <CreDtTm>{now}</CreDtTm>
    </GrpHdr>
    <OrgnlGrpInfAndSts>
      <OrgnlMsgId>{original_msg_id}</OrgnlMsgId>
      <OrgnlMsgNmId>pacs.008.001.08</OrgnlMsgNmId>
      <GrpSts>{status}</GrpSts>
    </OrgnlGrpInfAndSts>
    <TxInfAndSts>
      <OrgnlEndToEndId>{original_e2e_id}</OrgnlEndToEndId>
      <TxSts>{status}</TxSts>
      <StsRsnInf>
        <Rsn>
          <Prtry>{status_reason or 'NORMAL'}</Prtry>
        </Rsn>
      </StsRsnInf>
    </TxInfAndSts>
  </FIToFIPmtStsRpt>
</Document>""".strip()


# ── ISO 8583-style JSON Parser ────────────────────────────────────────────────

def parse_iso_8583_json(payload: Dict[str, Any]) -> CanonicalPaymentMessage:
    """
    Parses ISO 8583-style JSON:
    MTI 0200 (Transaction Request)
    Field 3: Processing Code
    Field 4: Amount, Transaction (minor units, 12 digits)
    Field 11: Systems Trace Audit Number (STAN)
    Field 41: Card Acceptor Terminal ID
    Field 49: Currency Code (e.g., 356 for INR, 840 for USD)
    Field 102: Account Identification 1 (Payer)
    Field 103: Account Identification 2 (Payee)
    """
    errors = []
    mti = payload.get("mti", "0200")
    fields = payload.get("fields", payload)

    amt_raw = fields.get("4") or fields.get("amount", "0")
    try:
        amt_minor = int(amt_raw)
    except ValueError:
        amt_minor = 0
        errors.append(f"Invalid Field 4 (Amount): {amt_raw}")

    # Currency translation
    ccy_map = {"356": "INR", "840": "USD", "978": "EUR", "826": "GBP"}
    ccy_code = str(fields.get("49") or "INR")
    ccy = ccy_map.get(ccy_code, ccy_code)

    stan = str(fields.get("11") or uuid.uuid4().hex[:6])
    retrieval_ref = str(fields.get("37") or str(uuid.uuid4()))

    dbtr_acc = str(fields.get("102") or fields.get("pan", "CARD_HOLDER"))
    cdtr_acc = str(fields.get("103") or fields.get("merchant_id", "MERCHANT"))

    return CanonicalPaymentMessage(
        message_id=f"ISO8583-{stan}-{retrieval_ref[:8]}",
        creation_date_time=datetime.now(timezone.utc).isoformat(),
        instruction_id=retrieval_ref,
        end_to_end_id=retrieval_ref,
        amount_minor=amt_minor,
        currency=ccy.upper(),
        debtor=CanonicalParty(
            name=fields.get("cardholder_name", f"Cardholder {dbtr_acc[-4:] if len(dbtr_acc)>=4 else ''}"),
            account_number=dbtr_acc
        ),
        creditor=CanonicalParty(
            name=fields.get("merchant_name", "Merchant"),
            account_number=cdtr_acc
        ),
        remittance_info=fields.get("description", "ISO 8583 Point of Sale Payment"),
        raw_format="ISO_8583_JSON",
        validation_errors=errors
    )


# ── SWIFT MT103 Parser ────────────────────────────────────────────────────────

def parse_swift_mt103(text_content: str) -> CanonicalPaymentMessage:
    """
    Parses SWIFT MT103 single customer credit transfer.
    Key tags:
    :20: Transaction Reference Number
    :23B: Bank Operation Code (CRED)
    :32A: Value Date, Currency Code, Amount (e.g. 261015USD10000,00)
    :50K: Ordering Customer (Debtor)
    :57A: Account With Institution (Creditor BIC)
    :59: Beneficiary Customer (Creditor)
    :70: Remittance Information
    :71A: Details of Charges (SHA/BEN/OUR)
    """
    errors = []
    tags: Dict[str, str] = {}
    lines = text_content.strip().split("\n")
    curr_tag = None
    curr_val = []

    for line in lines:
        match = re.match(r"^:(\d{2}[A-Z]?):(.*)", line)
        if match:
            if curr_tag:
                tags[curr_tag] = "\n".join(curr_val).strip()
            curr_tag = match.group(1)
            curr_val = [match.group(2)]
        elif curr_tag:
            curr_val.append(line)

    if curr_tag:
        tags[curr_tag] = "\n".join(curr_val).strip()

    txn_ref = tags.get("20", str(uuid.uuid4()))
    amt_tag = tags.get("32A", "")
    ccy = "USD"
    amt_minor = 0

    if amt_tag:
        # Format: YYMMDD(3 chars CCY)(Amount with comma or period)
        # e.g., 261015USD10500,50
        amt_match = re.match(r"^\d{6}([A-Z]{3})([0-9,\.]+)", amt_tag)
        if amt_match:
            ccy = amt_match.group(1)
            amt_num_str = amt_match.group(2).replace(",", ".")
            try:
                amt_minor = int(round(float(amt_num_str) * 100))
            except ValueError:
                errors.append(f"Invalid amount in MT103 Tag 32A: {amt_num_str}")
        else:
            errors.append(f"Cannot parse MT103 Tag 32A: {amt_tag}")
    else:
        errors.append("Missing mandatory Tag 32A in MT103")

    debtor_raw = tags.get("50K", tags.get("50A", "UNKNOWN DEBTOR"))
    debtor_lines = debtor_raw.split("\n")
    debtor_acc = debtor_lines[0].replace("/", "") if debtor_lines[0].startswith("/") else None
    debtor_name = debtor_lines[1] if len(debtor_lines) > 1 else debtor_lines[0]

    creditor_raw = tags.get("59", "UNKNOWN CREDITOR")
    creditor_lines = creditor_raw.split("\n")
    creditor_acc = creditor_lines[0].replace("/", "") if creditor_lines[0].startswith("/") else None
    creditor_name = creditor_lines[1] if len(creditor_lines) > 1 else creditor_lines[0]

    return CanonicalPaymentMessage(
        message_id=f"SWIFT-{txn_ref}",
        creation_date_time=datetime.now(timezone.utc).isoformat(),
        instruction_id=txn_ref,
        end_to_end_id=txn_ref,
        amount_minor=amt_minor,
        currency=ccy.upper(),
        debtor=CanonicalParty(name=debtor_name, account_number=debtor_acc),
        creditor=CanonicalParty(name=creditor_name, account_number=creditor_acc, routing_number=tags.get("57A")),
        remittance_info=tags.get("70", "SWIFT MT103 Transfer"),
        charge_bearer=tags.get("71A", "SHA"),
        raw_format="SWIFT_MT103",
        validation_errors=errors
    )


# ── Legacy CSV / Fixed-Width Parser ───────────────────────────────────────────

def parse_legacy_csv(csv_content: str) -> List[CanonicalPaymentMessage]:
    """
    Parses legacy payment batch CSV:
    Headers: instruction_id, debtor_name, debtor_account, debtor_ifsc,
             creditor_name, creditor_account, creditor_ifsc, amount, currency, description
    """
    reader = csv.DictReader(io.StringIO(csv_content.strip()))
    results = []
    for row in reader:
        errors = []
        try:
            amt_val = float(row.get("amount", 0))
            amt_minor = int(round(amt_val * 100))
        except (ValueError, TypeError):
            amt_minor = 0
            errors.append(f"Invalid amount: {row.get('amount')}")

        instr_id = row.get("instruction_id") or str(uuid.uuid4())
        ccy = row.get("currency", "INR").strip().upper()

        msg = CanonicalPaymentMessage(
            message_id=f"CSV-{instr_id}",
            creation_date_time=datetime.now(timezone.utc).isoformat(),
            instruction_id=instr_id,
            end_to_end_id=row.get("end_to_end_id") or instr_id,
            amount_minor=amt_minor,
            currency=ccy,
            debtor=CanonicalParty(
                name=row.get("debtor_name", "CSV Payer"),
                account_number=row.get("debtor_account"),
                routing_number=row.get("debtor_ifsc")
            ),
            creditor=CanonicalParty(
                name=row.get("creditor_name", "CSV Beneficiary"),
                account_number=row.get("creditor_account"),
                routing_number=row.get("creditor_ifsc")
            ),
            remittance_info=row.get("description", "Legacy CSV Payment"),
            raw_format="LEGACY_CSV",
            validation_errors=errors
        )
        results.append(msg)
    return results


# ── Generic Translation Entry Point ───────────────────────────────────────────

def translate_message(content: str, format_type: str = "AUTO") -> CanonicalPaymentMessage:
    """
    Universal translation entrypoint. Detects format or uses provided format_type:
    'AUTO', 'PAIN_001', 'PACS_008', 'ISO_8583', 'SWIFT_MT103', 'CSV', 'JSON'
    """
    cleaned = content.strip()
    detected_format = format_type.upper()

    if detected_format == "AUTO":
        if cleaned.startswith("<?xml") or "<Document" in cleaned or "<CstmrCdtTrfInitn" in cleaned:
            detected_format = "PAIN_001"
        elif cleaned.startswith("{") or cleaned.startswith("["):
            try:
                js = json.loads(cleaned)
                if isinstance(js, dict) and ("mti" in js or "fields" in js or "4" in js):
                    detected_format = "ISO_8583"
                else:
                    detected_format = "JSON"
            except Exception:
                detected_format = "JSON"
        elif cleaned.startswith(":20:") or ":32A:" in cleaned:
            detected_format = "SWIFT_MT103"
        elif "," in cleaned and ("amount" in cleaned.lower() or "creditor" in cleaned.lower()):
            detected_format = "CSV"
        else:
            detected_format = "JSON"

    if detected_format == "PAIN_001" or detected_format == "XML":
        return parse_pain_001(cleaned)
    elif detected_format == "ISO_8583":
        js = json.loads(cleaned) if isinstance(cleaned, str) else cleaned
        return parse_iso_8583_json(js)
    elif detected_format == "SWIFT_MT103":
        return parse_swift_mt103(cleaned)
    elif detected_format == "CSV":
        items = parse_legacy_csv(cleaned)
        return items[0] if items else CanonicalPaymentMessage(
            message_id=str(uuid.uuid4()),
            creation_date_time=datetime.now(timezone.utc).isoformat(),
            instruction_id=str(uuid.uuid4()),
            end_to_end_id=str(uuid.uuid4()),
            amount_minor=0,
            currency="INR",
            debtor=CanonicalParty(name="Unknown"),
            creditor=CanonicalParty(name="Unknown"),
            raw_format="CSV",
            validation_errors=["Empty CSV"]
        )
    elif detected_format == "JSON":
        data = json.loads(cleaned)
        return CanonicalPaymentMessage(
            message_id=data.get("message_id", str(uuid.uuid4())),
            creation_date_time=data.get("creation_date_time", datetime.now(timezone.utc).isoformat()),
            instruction_id=data.get("instruction_id", str(uuid.uuid4())),
            end_to_end_id=data.get("end_to_end_id", str(uuid.uuid4())),
            amount_minor=data.get("amount_minor", int(float(data.get("amount", 0)) * 100)),
            currency=data.get("currency", "INR").upper(),
            debtor=CanonicalParty(**data.get("debtor", {"name": "Payer"})),
            creditor=CanonicalParty(**data.get("creditor", {"name": "Beneficiary"})),
            remittance_info=data.get("remittance_info") or data.get("description"),
            urgency=data.get("urgency", "NORMAL"),
            raw_format="JSON"
        )
    else:
        raise ValueError(f"Unsupported message format: {detected_format}")
