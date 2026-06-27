import React from 'react';
import { interpolate, useCurrentFrame, spring, Img, useVideoConfig, staticFile } from 'remotion';
import { COLORS } from '../constants';
import { Caption, Kicker } from '../Caption';

export const Scene10_RiskAdjusted: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ position: 'absolute', inset: 0, background: COLORS.labSurface }}>
      <div style={{ position: 'absolute', inset: 0, opacity: 0.3, backgroundImage: `linear-gradient(rgba(82,215,247,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(82,215,247,0.08) 1px, transparent 1px)`, backgroundSize: '80px 80px' }} />

      <div style={{ position: 'relative', zIndex: 2, display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 660px', gap: 54, padding: '78px 84px', height: '100%' }}>
        <div style={{ alignSelf: 'center', minWidth: 0, height: 790, border: '1px solid rgba(255,255,255,0.18)', background: 'rgba(7,12,22,0.84)', boxShadow: '0 32px 80px rgba(0,0,0,0.42)', overflow: 'hidden', opacity: spring({ frame: frame - 10, fps }), transform: `translateY(${(1 - spring({ frame: frame - 10, fps })) * 46}px)` }}>
          <Img src={staticFile("/screenshots/strategy-result-risk.png")} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'left top' }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24 }}>
          <Kicker text="RISK ADJUSTED" delay={5} />
          <h2 style={{ margin: 0, fontWeight: 900, fontSize: 82, lineHeight: 0.94, color: '#f8fbff', opacity: spring({ frame: frame - 10, fps }) }}>
            不只看收益，也看风险质量。
          </h2>
          <p style={{ margin: 0, maxWidth: 660, fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 35, lineHeight: 1.38, color: '#d8e5f3', opacity: interpolate(frame - 16, [0, 12], [0, 1], { extrapolateRight: 'clamp' }) }}>
            夏普比率从 1.26 提升到 1.62；最大回撤从 -44.58% 收窄到 -31.01%。
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 20, maxWidth: 690 }}>
            <article style={{ minHeight: 178, padding: 24, border: `1px solid rgba(82,215,247,0.26)`, background: 'rgba(8,15,28,0.74)', opacity: interpolate(frame - 27, [0, 12], [0, 1], { extrapolateRight: 'clamp' }) }}>
              <b style={{ display: 'block', marginBottom: 12, fontSize: 34, color: '#f8fbff' }}>Sharpe</b>
              <p style={{ margin: 0, color: '#bfd1e6', fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 24 }}>1.26 → 1.62</p>
              <strong style={{ display: 'block', marginTop: 10, fontFamily: 'Inter, sans-serif', fontWeight: 900, fontSize: 58, color: COLORS.cyanSignal }}>+0.36</strong>
            </article>
            <article style={{
              minHeight: 178, padding: 24,
              border: `1px solid rgba(225,29,72,0.48)`,
              background: 'rgba(225,29,72,0.13)',
              opacity: interpolate(frame - 32, [0, 12], [0, 1], { extrapolateRight: 'clamp' }),
              transform: `scale(${1 + Math.sin(frame * 0.05) * 0.03})`,
            }}>
              <b style={{ display: 'block', marginBottom: 12, fontSize: 34, color: '#f8fbff' }}>Drawdown</b>
              <p style={{ margin: 0, color: '#bfd1e6', fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 24 }}>-44.58% → -31.01%</p>
              <strong style={{ display: 'block', marginTop: 10, fontFamily: 'Inter, sans-serif', fontWeight: 900, fontSize: 58, color: COLORS.quantumRose }}>改善 13.57%</strong>
            </article>
          </div>
        </div>
      </div>
      <Caption text="提升效果同时体现在收益、夏普和回撤三个维度。" timestamp="02:15" startFrame={30} />
    </div>
  );
};

export const Scene11_SingleStock: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ position: 'absolute', inset: 0, background: COLORS.contentSurface }}>
      <div style={{ position: 'absolute', inset: 0, opacity: 0.42, backgroundImage: `linear-gradient(rgba(16,32,51,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(16,32,51,0.08) 1px, transparent 1px)`, backgroundSize: '80px 80px' }} />

      <div style={{ position: 'relative', zIndex: 2, display: 'grid', gridTemplateColumns: '690px minmax(0, 1fr)', gap: 54, padding: '78px 84px', height: '100%' }}>
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 12, width: 'fit-content', minHeight: 36, padding: '7px 13px', border: `1px solid rgba(47,109,246,0.28)`, color: COLORS.modelTeal, fontFamily: '"JetBrains Mono", monospace', fontWeight: 700, fontSize: 20, textTransform: 'uppercase', opacity: interpolate(frame - 5, [0, 12], [0, 1], { extrapolateRight: 'clamp' }) }}>
            CLICK A STOCK
          </div>
          <h2 style={{ margin: 0, fontWeight: 900, fontSize: 82, lineHeight: 0.94, color: COLORS.textDark, opacity: spring({ frame: frame - 10, fps }) }}>
            胜宏科技，单股验证闭环。
          </h2>
          <p style={{ margin: 0, maxWidth: 660, fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 35, lineHeight: 1.38, color: '#334155', opacity: interpolate(frame - 16, [0, 12], [0, 1], { extrapolateRight: 'clamp' }) }}>
            模型页点击股票后，页面直接运行单股回测。累计收益从 362.88% 到 1707.68%，夏普从 1.269 到 1.895。
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 20, maxWidth: 690 }}>
            <article style={{ minHeight: 178, padding: 24, border: `1px solid ${COLORS.borderSoft}`, background: 'rgba(255,255,255,0.92)', opacity: interpolate(frame - 27, [0, 12], [0, 1], { extrapolateRight: 'clamp' }) }}>
              <b style={{ display: 'block', marginBottom: 12, fontSize: 34, color: COLORS.textDark }}>原始路径</b>
              <p style={{ margin: 0, color: '#475569', fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 24 }}>累计收益率</p>
              <strong style={{ display: 'block', marginTop: 10, fontFamily: 'Inter, sans-serif', fontWeight: 900, fontSize: 58, color: COLORS.modelTeal }}>362.88%</strong>
            </article>
            <article style={{
              minHeight: 178, padding: 24,
              border: `1px solid rgba(225,29,72,0.48)`,
              background: 'rgba(225,29,72,0.13)',
              opacity: interpolate(frame - 32, [0, 12], [0, 1], { extrapolateRight: 'clamp' }),
              transform: `scale(${1 + Math.sin(frame * 0.05) * 0.03})`,
            }}>
              <b style={{ display: 'block', marginBottom: 12, fontSize: 34, color: COLORS.textDark }}>PT 路径</b>
              <p style={{ margin: 0, color: '#475569', fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 24 }}>累计收益率</p>
              <strong style={{ display: 'block', marginTop: 10, fontFamily: 'Inter, sans-serif', fontWeight: 900, fontSize: 58, color: COLORS.quantumRose }}>1707.68%</strong>
            </article>
          </div>
        </div>

        <div style={{ alignSelf: 'center', minWidth: 0, height: 790, border: `1px solid ${COLORS.borderSoft}`, background: '#ffffff', boxShadow: '0 30px 70px rgba(16,32,51,0.18)', overflow: 'hidden', opacity: spring({ frame: frame - 14, fps }), transform: `translateY(${(1 - spring({ frame: frame - 14, fps })) * 46}px)` }}>
          <Img src={staticFile("/screenshots/model-stock-result.png")} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'left top' }} />
        </div>
      </div>

      <div style={{ position: 'absolute', left: 84, right: 84, bottom: 46, zIndex: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 28, minHeight: 70, padding: '16px 24px', border: `1px solid ${COLORS.borderSoft}`, background: 'rgba(255,255,255,0.9)', color: COLORS.textDark, opacity: interpolate(frame - 30, [0, 18], [0, 1], { extrapolateRight: 'clamp' }) }}>
        <span style={{ fontFamily: 'Inter, "PingFang SC", sans-serif', fontWeight: 700, fontSize: 32 }}>从总览表格点击到单股曲线，验证过程被完整展现。</span>
        <code style={{ flexShrink: 0, color: COLORS.primaryBlue, fontWeight: 800, fontSize: 22, fontFamily: '"JetBrains Mono", monospace' }}>02:30</code>
      </div>
    </div>
  );
};
