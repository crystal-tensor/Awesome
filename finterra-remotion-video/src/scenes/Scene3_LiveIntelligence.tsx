import React from 'react';
import { interpolate, useCurrentFrame, spring, Img, useVideoConfig, staticFile } from 'remotion';
import { COLORS } from '../constants';
import { Caption, Kicker, ProofCard } from '../Caption';

export const Scene3_LiveIntelligence: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ position: 'absolute', inset: 0, background: COLORS.labSurface }}>
      <div style={{
        position: 'absolute', inset: 0, opacity: 0.3,
        backgroundImage: `linear-gradient(rgba(82,215,247,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(82,215,247,0.08) 1px, transparent 1px)`,
        backgroundSize: '80px 80px',
      }} />
      <div style={{
        position: 'absolute', inset: 0,
        background: `radial-gradient(circle at 18% 18%, rgba(82,215,247,0.22), transparent 28%)`,
        opacity: 0.92,
      }} />

      <div style={{
        position: 'relative', zIndex: 2,
        display: 'grid', gridTemplateColumns: '690px minmax(0, 1fr)',
        gap: 54, padding: '78px 84px', height: '100%',
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24 }}>
          <Kicker text="LIVE INTELLIGENCE" delay={5} />
          <h2 style={{
            margin: 0, fontWeight: 900, fontSize: 82, lineHeight: 0.94, color: '#f8fbff',
            opacity: spring({ frame: frame - 10, fps }),
            transform: `translateY(${(1 - spring({ frame: frame - 10, fps })) * 54}px)`,
          }}>
            市场新闻被编织成金融图谱。
          </h2>
          <p style={{
            margin: 0, maxWidth: 660, fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 35, lineHeight: 1.38, color: '#d8e5f3',
            opacity: interpolate(frame - 18, [0, 12], [0, 1], { extrapolateRight: 'clamp' }),
          }}>
            系统读取真实资讯源，抽取资产、区域、实体和事件，让宏观风险以节点和关系呈现。
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 14, maxWidth: 690 }}>
            <ProofCard label="NEWS" value="377" delay={30} />
            <ProofCard label="NODES" value="1,277" delay={35} />
            <ProofCard label="EDGES" value="2,761" delay={40} />
          </div>
        </div>

        <div style={{
          alignSelf: 'center', minWidth: 0, height: 790,
          border: '1px solid rgba(255,255,255,0.18)',
          background: 'rgba(7,12,22,0.84)', boxShadow: '0 32px 80px rgba(0,0,0,0.42)',
          overflow: 'hidden',
          opacity: spring({ frame: frame - 16, fps }),
          transform: `translateY(${(1 - spring({ frame: frame - 16, fps })) * 46}px)`,
        }}>
          <Img src={staticFile('/screenshots/lab-hero-proof.png')} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center' }} />
        </div>
      </div>

      <Caption text="377 条资讯、1,277 个节点、2,761 条关系，成为可追踪的市场网络。" timestamp="00:30" startFrame={30} />
    </div>
  );
};
