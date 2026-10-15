"""Unit tests for message translation: ISO 20022, ISO 8583, SWIFT MT103, and CSV."""
from app.services.translation_service import (
    translate_message, serialize_pain_001, serialize_pacs_008,
    CanonicalPaymentMessage, CanonicalParty
)


def test_parse_and_serialize_pain_001_roundtrip():
    xml_sample = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.09">
  <CstmrCdtTrfInitn>
    <GrpHdr>
      <MsgId>MSG-TEST-001</MsgId>
      <CreDtTm>2026-10-15T10:00:00Z</CreDtTm>
      <NbOfTxs>1</NbOfTxs>
      <InitgPty><Nm>Acme Corp</Nm></InitgPty>
    </GrpHdr>
    <PmtInf>
      <PmtInfId>PMT-001</PmtInfId>
      <PmtMtd>TRF</PmtMtd>
      <Dbtr><Nm>Acme Corp</Nm></Dbtr>
      <DbtrAcct><Id><Othr><Id>ACC12345</Id></Othr></Id></DbtrAcct>
      <CdtTrfTxInf>
        <PmtId><InstrId>INS-001</InstrId><EndToEndId>E2E-001</EndToEndId></PmtId>
        <Amt><InstdAmt Ccy="INR">1500.50</InstdAmt></Amt>
        <Cdtr><Nm>Zenith Cloud</Nm></Cdtr>
        <CdtrAcct><Id><Othr><Id>ACC67890</Id></Othr></Id></CdtrAcct>
        <RmtInf><Ustrd>Retainer Fee</Ustrd></RmtInf>
      </CdtTrfTxInf>
    </PmtInf>
  </CstmrCdtTrfInitn>
</Document>"""

    canonical = translate_message(xml_sample, "PAIN_001")
    assert canonical.amount_minor == 150050
    assert canonical.currency == "INR"
    assert canonical.debtor.name == "Acme Corp"
    assert canonical.creditor.name == "Zenith Cloud"

    # Re-serialize
    serialized_xml = serialize_pain_001(canonical)
    assert "<MsgId>MSG-TEST-001</MsgId>" in serialized_xml
    assert "1500.50" in serialized_xml


def test_parse_iso_8583_json():
    payload = """{
      "mti": "0200",
      "fields": {
        "4": "450000",
        "49": "356",
        "102": "411111XXXXXX1111",
        "cardholder_name": "Rohan Sharma",
        "merchant_name": "Reliance Retail"
      }
    }"""
    canonical = translate_message(payload, "ISO_8583")
    assert canonical.amount_minor == 450000
    assert canonical.currency == "INR"
    assert canonical.debtor.name == "Rohan Sharma"


def test_parse_swift_mt103():
    swift_text = """:20:SWIFT20261015099
:23B:CRED
:32A:261015USD12500,00
:50K:/US8899112233
Global Logistics Corp
:59:/IN1122334455
Apex Engineering
:70:License fee"""
    canonical = translate_message(swift_text, "SWIFT_MT103")
    assert canonical.amount_minor == 1250000
    assert canonical.currency == "USD"
    assert "Global Logistics" in canonical.debtor.name
    assert "Apex Engineering" in canonical.creditor.name
