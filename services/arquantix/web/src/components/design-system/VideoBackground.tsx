"use client";

export interface VideoBackgroundProps {
  videoSrc: string;
  children?: React.ReactNode;
}

export function VideoBackground({ videoSrc, children }: VideoBackgroundProps) {
  return (
    <div className="relative size-full">
      <video
        autoPlay
        className="absolute max-w-none object-cover size-full"
        controlsList="nodownload"
        loop
        playsInline
      >
        <source src={videoSrc} />
      </video>
      {children}
    </div>
  );
}
