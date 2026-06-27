import React from 'react';
import { interpolate, useCurrentFrame, spring, useVideoConfig } from 'remotion';
import { COLORS } from '../constants';
import { Caption, Kicker } from '../Caption';

const pillars = [
  { title: '实时资讯图谱', desc: '把 news 目录、RSS 快照和资产节点重新编织成市场关系网。' },
  { title: 'MiroFish 推演', desc: '围绕同一个问题生成角色、交叉质询、收敛分歧。' },
  { title: 'PT 合成数据', desc: '用重尾先验生成更关注极端状态的 OHLCV 路径。' },
  { title: '策略对照验证', desc: '同一套策略，在真实路径与 PT 路径上并排回测。' },
];

export const Scene2_OneWorkbench: React.FC = () => {
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
        background: `radial-gradient(circle at 18% 18%, rgba(82,215,247,0.22), transparent 28%), radial-gradient(circle at 78% 72%, rgba(225,29,72,0.16), transparent 26%)`,
        opacity: 0.92,
      }} />

      <div style={{
        position: 'relative', zIndex: 2,
        display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 660px',
        gap: 54, padding: '78px 84px', height: '100%',
      }}>
        <div style={{ alignSelf: 'center', display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 20 }}>
          {pillars.map((p, i) => {
            const delay = 27 + i * 8;
            const opacity = interpolate(frame - delay, [0, 12], [0, 1], { extrapolateRight: 'clamp' });
            const y = interpolate(frame - delay, [0, 12], [32, 0], { extrapolateRight: 'clamp' });
            return (
              <article key={i} style={{
                minHeight: 178, padding: 24,
                border: `1px solid rgba(82,215,247,0.26)`,
                background: 'rgba(8,15,28,0.74)',
                opacity, transform: `translateY(${y}px)`,
              }}>
                <b style={{ display: 'block', marginBottom: 12, fontSize: 34, lineHeight: 1.05, color: '#f8fbff' }}>{p.title}</b>
                <p style={{ margin: 0, color: '#bfd1e6', fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 24, lineHeight: 1.32 }}>{p.desc}</p>
              </article>
            );
          })}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24 }}>
          <Kicker text="ONE WORKBENCH" delay={5} />
          <h2 style={{
            margin: 0, maxWidth: 720, fontWeight: 900, fontSize: 82, lineHeight: 0.94, color: '#f8fbff',
            opacity: spring({ frame: frame - 10, fps }),
            transform: `translateY(${(1 - spring({ frame: frame - 10, fps })) * 54}px)`,
          }}>
            从资讯，到模型，到可复盘的收益证据。
          </h2>
          <p style={{
            maxWidth: 660, fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 35, lineHeight: 1.38, color: '#d8e5f3',
            opacity: interpolate(frame - 18, [0, 12], [0, 1], { extrapolateRight: 'clamp' }), margin: 0,
          }}>
            FinTerra 不是把 AI 做成聊天框，而是把金融研究流程做成可运行、可验证的工作台。
          </p>
        </div>
      </div>
      <Caption text="资讯、推演、合成数据、策略验证，连成一条证据链。" timestamp="00:15" startFrame={30} />
    </div>
  );
};
