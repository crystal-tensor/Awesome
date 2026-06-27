import React from 'react';
import { interpolate, useCurrentFrame, spring, useVideoConfig } from 'remotion';
import { COLORS } from '../constants';
import { Caption } from '../Caption';

const pipelineSteps = [
  { num: '01', title: '资讯有图谱', desc: '377 条新闻进入资产关系网络。' },
  { num: '02', title: '推演有过程', desc: '角色生成、三轮讨论、交叉质询可见。' },
  { num: '03', title: '模型有验证', desc: '16,944 个成功标的支撑市场级证据。' },
  { num: '04', title: '策略有对照', desc: '普通路径与 PT 路径并排回测。' },
];

export const Scene12_CTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fadeOutStart = 450 - 27; // last 27 frames fade out (15*30=450)

  const sceneOpacity = frame > fadeOutStart
    ? interpolate(frame, [fadeOutStart, 450], [1, 0], { extrapolateRight: 'clamp' })
    : 1;

  return (
    <div style={{ position: 'absolute', inset: 0, background: COLORS.labSurface, opacity: sceneOpacity }}>
      <div style={{ position: 'absolute', inset: 0, opacity: 0.3, backgroundImage: `linear-gradient(rgba(82,215,247,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(82,215,247,0.08) 1px, transparent 1px)`, backgroundSize: '80px 80px' }} />
      <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(circle at 60% 40%, rgba(82,215,247,0.12), transparent 40%)`, opacity: 0.92 }} />

      <div style={{ position: 'relative', zIndex: 2, display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 660px', gap: 54, padding: '78px 84px', height: '100%' }}>
        {/* Pipeline on left */}
        <div style={{ alignSelf: 'center', display: 'grid', gap: 18 }}>
          {pipelineSteps.map((step, i) => {
            const delay = 10 + i * 14;
            const op = interpolate(frame - delay, [0, 12], [0, 1], { extrapolateRight: 'clamp' });
            const y = interpolate(frame - delay, [0, 12], [32, 0], { extrapolateRight: 'clamp' });
            return (
              <div key={i} style={{
                display: 'grid', gridTemplateColumns: '100px minmax(0, 1fr)',
                alignItems: 'center', gap: 18,
                minHeight: 102, padding: 22,
                border: `1px solid rgba(82,215,247,0.25)`,
                background: 'rgba(8,15,28,0.72)',
                opacity: op, transform: `translateY(${y}px)`,
              }}>
                <span style={{ color: COLORS.cyanSignal, fontFamily: '"JetBrains Mono", monospace', fontWeight: 900, fontSize: 34 }}>{step.num}</span>
                <div>
                  <b style={{ fontSize: 34, color: '#f8fbff' }}>{step.title}</b>
                  <p style={{ margin: '4px 0 0', color: '#bfd1e6', fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 22, lineHeight: 1.32 }}>{step.desc}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Brand + CTA on right */}
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24 }}>
          {/* Brand lockup */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 18,
            opacity: interpolate(frame - 5, [0, 15], [0, 1], { extrapolateRight: 'clamp' }),
          }}>
            <div style={{
              width: 64, height: 64, borderRadius: '50%',
              border: `2px solid rgba(82,215,247,0.6)`,
              background: `radial-gradient(circle at 30% 28%, #ffffff, rgba(255,255,255,0) 18%), radial-gradient(circle at 58% 62%, ${COLORS.cyanSignal}, rgba(82,215,247,0) 45%), ${COLORS.sidebarNavy}`,
            }} />
            <span style={{ fontFamily: 'Inter, sans-serif', fontWeight: 900, fontSize: 82, color: '#f8fbff' }}>FinTerra</span>
          </div>

          <h2 style={{
            margin: 0, fontWeight: 900, fontSize: 82, lineHeight: 0.94, color: '#f8fbff',
            opacity: spring({ frame: frame - 10, fps }),
          }}>
            让金融研究，从观点走向证据。
          </h2>
          <p style={{
            margin: 0, maxWidth: 660, fontFamily: 'Inter, sans-serif', fontWeight: 500,
            fontSize: 35, lineHeight: 1.38, color: '#d8e5f3',
            opacity: interpolate(frame - 16, [0, 12], [0, 1], { extrapolateRight: 'clamp' }),
          }}>
            访问本地演示，查看资讯推演、合成数据模型和策略回测工作台。
          </p>
          <p style={{
            margin: 0, fontFamily: 'Inter, sans-serif', fontWeight: 600,
            fontSize: 24, lineHeight: 1.35, color: '#cbd5e1',
            opacity: interpolate(frame - 22, [0, 12], [0, 1], { extrapolateRight: 'clamp' }),
          }}>
            研究工具，不构成投资建议、交易指令或收益承诺。
          </p>
        </div>
      </div>
      <Caption text="FinTerra：资讯、模型、策略，一条可验证的研究链路。" timestamp="03:00" startFrame={30} />
    </div>
  );
};
