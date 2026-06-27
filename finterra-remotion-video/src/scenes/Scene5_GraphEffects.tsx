import React from 'react';
import { interpolate, useCurrentFrame, spring, Img, useVideoConfig, staticFile } from 'remotion';
import { COLORS } from '../constants';
import { Caption, Kicker, ProofCard } from '../Caption';

export const Scene5_GraphEffects: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pulse = Math.sin(frame * 0.03) * 0.5 + 0.5;

  return (
    <div style={{ position: 'absolute', inset: 0, background: COLORS.labSurface }}>
      <div style={{ position: 'absolute', inset: 0, opacity: 0.3, backgroundImage: `linear-gradient(rgba(82,215,247,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(82,215,247,0.08) 1px, transparent 1px)`, backgroundSize: '80px 80px' }} />
      <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(circle at 50% 50%, rgba(82,215,247,0.15), transparent 35%)`, opacity: 0.92 }} />

      <div style={{ position: 'relative', zIndex: 2, display: 'grid', gridTemplateColumns: '690px minmax(0, 1fr)', gap: 54, padding: '78px 84px', height: '100%' }}>
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24 }}>
          <Kicker text="GRAPH EFFECTS" delay={5} />
          <h2 style={{ margin: 0, fontWeight: 900, fontSize: 82, lineHeight: 0.94, color: '#f8fbff', opacity: spring({ frame: frame - 10, fps }) }}>
            节点和边，随着讨论主题闪烁。
          </h2>
          <p style={{ margin: 0, maxWidth: 660, fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 35, lineHeight: 1.38, color: '#d8e5f3', opacity: interpolate(frame - 16, [0, 12], [0, 1], { extrapolateRight: 'clamp' }) }}>
            风险传导从一段解释，变成一张会响应的网络。研究员可以看到系统正在关注哪些资产、区域和事件。
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 14, maxWidth: 690 }}>
            <ProofCard label="PROCESS" value="三轮讨论" delay={25} />
            <ProofCard label="VIEW" value="二维 / 三维" delay={30} />
          </div>
        </div>

        <div style={{ alignSelf: 'center', display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 24, opacity: spring({ frame: frame - 14, fps }) }}>
          <div style={{ height: 700, border: '1px solid rgba(255,255,255,0.18)', background: 'rgba(7,12,22,0.84)', overflow: 'hidden', boxShadow: `0 0 ${40 + pulse * 20}px rgba(82,215,247,0.3)` }}>
            <Img src={staticFile("/screenshots/lab-generating-mid.png")} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
          </div>
          <div style={{ height: 700, border: '1px solid rgba(255,255,255,0.18)', background: 'rgba(7,12,22,0.84)', overflow: 'hidden', boxShadow: `0 0 ${40 + (1 - pulse) * 20}px rgba(82,215,247,0.35)` }}>
            <Img src={staticFile("/screenshots/lab-graph-3d.png")} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'center' }} />
          </div>
        </div>
      </div>
      <Caption text="特殊效果被放在画面中心：闪烁图谱、过程流、二维与三维视图。" timestamp="01:00" startFrame={30} />
    </div>
  );
};
