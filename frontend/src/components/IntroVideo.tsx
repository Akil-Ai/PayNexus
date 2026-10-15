import React, { useRef, useState, useEffect } from 'react';
import { Play, Volume2, VolumeX, SkipForward } from 'lucide-react';

interface IntroVideoProps {
  onComplete: () => void;
}

export const IntroVideo: React.FC<IntroVideoProps> = ({ onComplete }) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isMuted, setIsMuted] = useState(true);
  const [canSkip, setCanSkip] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    video.defaultMuted = true;
    video.muted = true;
    const playPromise = video.play();
    if (playPromise !== undefined) {
      playPromise
        .then(() => setIsPlaying(true))
        .catch(() => {
          setIsPlaying(false);
        });
    }
  }, []);

  const handleTimeUpdate = () => {
    const video = videoRef.current;
    if (video && video.duration) {
      setProgress((video.currentTime / video.duration) * 100);
      if (!isPlaying && !video.paused) {
        setIsPlaying(true);
      }
    }
  };

  const handleManualPlay = () => {
    const video = videoRef.current;
    if (video) {
      video.muted = true;
      video.play().then(() => setIsPlaying(true)).catch(() => {});
    }
  };

  const toggleSound = () => {
    const video = videoRef.current;
    if (video) {
      video.muted = !video.muted;
      setIsMuted(video.muted);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black flex items-center justify-center overflow-hidden select-none">
      <video
        ref={videoRef}
        src="/intro-video.mp4"
        className="w-full h-full object-cover"
        playsInline
        autoPlay
        muted
        preload="auto"
        onPlay={() => setIsPlaying(true)}
        onTimeUpdate={handleTimeUpdate}
        onEnded={onComplete}
        onError={(e) => {
          console.warn("Video playback error or unsupported format, proceeding to Login", e);
          onComplete();
        }}
      />

      {/* Subtle overlay gradient at the bottom */}
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/30 pointer-events-none" />

      {/* Top Header Controls */}
      <div className="absolute top-6 left-6 right-6 flex items-center justify-between z-10">
        <div className="flex items-center gap-3 bg-black/40 backdrop-blur-md px-4 py-2 rounded-full border border-white/10">
          <img src="/paynexus-logo.png" alt="PayNexus" className="w-6 h-6 object-contain" />
          <span className="text-white text-xs font-semibold tracking-wider uppercase font-mono">
            PayNexus Intro
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={toggleSound}
            className="flex items-center gap-2 bg-black/50 hover:bg-black/70 backdrop-blur-md text-white/90 px-3.5 py-2 rounded-full border border-white/15 transition text-xs font-medium"
            title={isMuted ? "Unmute" : "Mute"}
          >
            {isMuted ? (
              <>
                <VolumeX className="w-4 h-4 text-amber-400" />
                <span>Unmute</span>
              </>
            ) : (
              <>
                <Volume2 className="w-4 h-4 text-emerald-400" />
                <span>Muted</span>
              </>
            )}
          </button>

          {canSkip && (
            <button
              onClick={onComplete}
              className="flex items-center gap-1.5 bg-gradient-to-r from-blue-600 to-emerald-500 hover:from-blue-500 hover:to-emerald-400 text-white px-4 py-2 rounded-full text-xs font-semibold tracking-wide shadow-lg shadow-emerald-500/20 transition transform active:scale-95"
            >
              <span>Skip to Login</span>
              <SkipForward className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Center Play button if autoplay blocked */}
      {!isPlaying && (
        <button
          onClick={handleManualPlay}
          className="absolute z-20 flex flex-col items-center gap-3 bg-white/10 hover:bg-white/20 backdrop-blur-md p-6 rounded-3xl border border-white/20 transition text-white shadow-2xl"
        >
          <div className="w-16 h-16 rounded-full bg-emerald-500 flex items-center justify-center text-slate-950 shadow-lg shadow-emerald-500/40">
            <Play className="w-8 h-8 translate-x-0.5 fill-current" />
          </div>
          <span className="text-sm font-semibold tracking-wide">Click to Play Introduction</span>
        </button>
      )}

      {/* Bottom Progress Bar */}
      <div className="absolute bottom-0 left-0 right-0 h-1.5 bg-white/10 z-10">
        <div
          className="h-full bg-gradient-to-r from-blue-500 via-sky-400 to-emerald-400 transition-all duration-100"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
};
