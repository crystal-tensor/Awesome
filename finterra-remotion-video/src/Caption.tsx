import React from 'react';
import { interpolate, useCurrentFrame, useVideoConfig } from 'remotion';
import { COLORS } from './constants';

export const Caption: React.FC<{
  text: string;
  timestamp: string;
  startFrame?: number;
}> = ({ text, timestamp, startFrame = 0 }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  const relativeFrame = frame - startFrame;
  const opacity = interpolate(relativeFrame, [0, 18], [0, 1], { extrapolateRight: 'clamp' });
  const y = interpolate(relativeFrame, [0, 18], [26, 0], { extrapolateRight: 'clamp' });

  return (
    <div
      style={{
        position: 'absolute',
        left: 84,
        right: 84,
        bottom: 46,
        zIndex: 10,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 28,
        minHeight: 70,
        padding: '16px 24px',
        border: `1px solid rgba(82, 215, 247, 0.25)`,
        background: 'rgba(8, 15, 28, 0.82)',
        opacity,
        transform: `translateY(${y}px)`,
      }}
    >
      <span
        style={{
          fontFamily: 'Inter, "PingFang SC", sans-serif',
          fontWeight: 700,
          fontSize: 32,
          lineHeight: 1.25,
          color: '#f8fbff',
        }}
      >
        {text}
      </span>
      <code
        style={{
          flexShrink: 0,
          color: COLORS.cyanSignal,
          fontWeight: 800,
          fontSize: 22,
          fontFamily: '"JetBrains Mono", monospace',
        }}
      >
        {timestamp}
      </code>
    </div>
  );
};

export const Kicker: React.FC<{ text: string; delay?: number }> = ({ text, delay = 0 }) => {
  const frame = useCurrentFrame();
  const relativeFrame = frame - delay;

  const opacity = interpolate(relativeFrame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const x = interpolate(relativeFrame, [0, 15], [-42, 0], { extrapolateRight: 'clamp' });

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 12,
        width: 'fit-content',
        minHeight: 36,
        padding: '7px 13px',
        border: `1px solid rgba(82, 215, 247, 0.42)`,
        color: COLORS.cyanSignal,
        fontFamily: '"JetBrains Mono", monospace',
        fontWeight: 700,
        fontSize: 20,
        textTransform: 'uppercase',
        opacity,
        transform: `translateX(${x}px)`,
      }}
    >
      {text}
    </div>
  );
};

export const ProofCard: React.FC<{
  label: string;
  value: string;
  delay?: number;
}> = ({ label, value, delay = 0 }) => {
  const frame = useCurrentFrame();
  const relativeFrame = frame - delay;

  const opacity = interpolate(relativeFrame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const y = interpolate(relativeFrame, [0, 15], [32, 0], { extrapolateRight: 'clamp' });

  return (
    <div
      style={{
        minWidth: 156,
        padding: '18px 20px',
        border: `1px solid rgba(82, 215, 247, 0.28)`,
        background: 'rgba(8, 15, 28, 0.72)',
        opacity,
        transform: `translateY(${y}px)`,
      }}
    >
      <small
        style={{
          display: 'block',
          marginBottom: 8,
          color: '#9fb0c5',
          fontFamily: '"JetBrains Mono", monospace',
          fontWeight: 700,
          fontSize: 18,
        }}
      >
        {label}
      </small>
      <strong
        style={{
          display: 'block',
          fontFamily: 'Inter, sans-serif',
          fontWeight: 900,
          fontSize: 44,
          color: '#ffffff',
        }}
      >
        {value}
      </strong>
    </div>
  );
};
