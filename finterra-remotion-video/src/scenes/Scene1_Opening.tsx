import React from 'react';
import { interpolate, useCurrentFrame, spring, Img, useVideoConfig, staticFile } from 'remotion';
import { COLORS } from '../constants';
import { Caption, Kicker, ProofCard } from '../Caption';

export const Scene1_Opening: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Fade in animations
  const sceneOpacity = interpolate(frame, [0, 10], [0, 1], { extrapolateRight: 'clamp' });
  const titleY = spring({ frame, fps, config: { damping: 12, stiffness: 80 } });
  const screenY = spring({ frame: frame - 12, fps, config: { damping: 18, stiffness: 60 } });
  const screenScale = interpolate(frame, [30, 450], [1, 1.04], { extrapolateRight: 'clamp' });

  return (
    <div style={{ position: 'absolute', inset: 0, background: COLORS.labSurface, opacity: sceneOpacity }}>
      {/* Grid background */}
      <div style={{
        position: 'absolute', inset: 0, opacity: 0.3,
        backgroundImage: `linear-gradient(rgba(82,215,247,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(82,215,247,0.08) 1px, transparent 1px)`,
        backgroundSize: '80px 80px',
      }} />

      {/* Glow */}
      <div style={{
        position: 'absolute', inset: 0,
        background: `radial-gradient(circle at 18% 18%, rgba(82,215,247,0.22), transparent 28%), radial-gradient(circle at 78% 72%, rgba(225,29,72,0.16), transparent 26%)`,
        opacity: 0.92,
      }} />

      <div style={{
        position: 'relative', zIndex: 2,
        display: 'grid', gridTemplateColumns: '690px minmax(0, 1fr)',
        gap: 54, padding: '78px 84px', height: '100%',
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24 }}>
          <Kicker text="FINTERRA RESEARCH OS" delay={5} />
          <h1 style={{
            margin: 0, maxWidth: 720, fontWeight: 900, fontSize: 118,
            lineHeight: 0.94, color: '#f8fbff',
            opacity: spring({ frame: frame - 10, fps, config: { damping: 15 } }),
            transform: `translateY(${(1 - spring({ frame: frame - 10, fps, config: { damping: 15 } })) * 54}px)`,
          }}>
            金融决策，不能只靠一张报表。
          </h1>
          <p style={{
            maxWidth: 660, fontFamily: 'Inter, sans-serif', fontWeight: 500,
            fontSize: 35, lineHeight: 1.38, color: '#d8e5f3',
            opacity: interpolate(frame - 20, [0, 15], [0, 1], { extrapolateRight: 'clamp' }),
            margin: 0,
          }}>
            当新闻、资产、模型和回测分散在不同工具里，真正的风险往往藏在传导路径中。
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 14, maxWidth: 690 }}>
            <ProofCard label="入口" value="资讯图谱" delay={25} />
            <ProofCard label="方法" value="多智能体推演" delay={30} />
          </div>
        </div>

        <div style={{
          alignSelf: 'center', minWidth: 0, height: 790,
          border: '1px solid rgba(255,255,255,0.18)',
          background: 'rgba(7,12,22,0.84)',
          boxShadow: '0 32px 80px rgba(0,0,0,0.42)',
          overflow: 'hidden',
          opacity: spring({ frame: frame - 16, fps }),
          transform: `translateY(${(1 - spring({ frame: frame - 16, fps })) * 46}px) scale(${screenScale})`,
        }}>
          <Img
            src={staticFile('/screenshots/lab-hero.png')}
            style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center top' }}
          />
        </div>
      </div>

      <Caption text="从一个问题，进入完整的金融研究链路。" timestamp="00:00" startFrame={30} />
    </div>
  );
};
