import React from 'react';
import { interpolate, useCurrentFrame, spring, Img, useVideoConfig, staticFile } from 'remotion';
import { COLORS } from '../constants';
import { Caption, Kicker } from '../Caption';

export const Scene4_ClickSend: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ position: 'absolute', inset: 0, background: COLORS.labSurface }}>
      <div style={{
        position: 'absolute', inset: 0, opacity: 0.3,
        backgroundImage: `linear-gradient(rgba(82,215,247,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(82,215,247,0.08) 1px, transparent 1px)`,
        backgroundSize: '80px 80px',
      }} />
      <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(circle at 80% 20%, rgba(82,215,247,0.18), transparent 28%)`, opacity: 0.92 }} />

      <div style={{
        position: 'relative', zIndex: 2,
        display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 660px',
        gap: 54, padding: '78px 84px', height: '100%',
      }}>
        <div style={{
          alignSelf: 'center', minWidth: 0, height: 790,
          border: '1px solid rgba(255,255,255,0.18)', background: 'rgba(7,12,22,0.84)',
          boxShadow: `0 0 ${30 + Math.sin(frame * 0.05) * 20}px rgba(82,215,247,0.42)`,
          overflow: 'hidden',
          opacity: spring({ frame: frame - 10, fps }),
          transform: `translateY(${(1 - spring({ frame: frame - 10, fps })) * 46}px)`,
        }}>
          <Img src={staticFile("/screenshots/lab-generating-early.png")} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24 }}>
          <Kicker text="CLICK SEND" delay={5} />
          <h2 style={{
            margin: 0, fontWeight: 900, fontSize: 82, lineHeight: 0.94, color: '#f8fbff',
            opacity: spring({ frame: frame - 10, fps }),
          }}>
            点击发送，推演开始。
          </h2>
          <p style={{
            margin: 0, maxWidth: 660, fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 35, lineHeight: 1.38, color: '#d8e5f3',
            opacity: interpolate(frame - 16, [0, 12], [0, 1], { extrapolateRight: 'clamp' }),
          }}>
            角色生成、证据读取、三轮讨论和交叉质询，不再藏在后端日志里，而是直接成为研究过程的一部分。
          </p>
          <p style={{
            margin: 0, fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 24, lineHeight: 1.35, color: '#cbd5e1',
            opacity: interpolate(frame - 26, [0, 12], [0, 1], { extrapolateRight: 'clamp' }),
          }}>
            画面中的过程流来自真实点击后的中间生成状态。
          </p>
        </div>
      </div>
      <Caption text="这里展示的不是静态页面，而是提交后的生成过程。" timestamp="00:45" startFrame={30} />
    </div>
  );
};
