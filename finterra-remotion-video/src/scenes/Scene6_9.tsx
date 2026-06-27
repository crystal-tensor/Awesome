import React from 'react';
import { interpolate, useCurrentFrame, spring, Img, useVideoConfig, staticFile } from 'remotion';
import { COLORS } from '../constants';
import { Caption, Kicker, ProofCard } from '../Caption';

export const Scene6_SyntheticData: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ position: 'absolute', inset: 0, background: COLORS.contentSurface }}>
      <div style={{ position: 'absolute', inset: 0, opacity: 0.42, backgroundImage: `linear-gradient(rgba(16,32,51,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(16,32,51,0.08) 1px, transparent 1px)`, backgroundSize: '80px 80px' }} />
      <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(circle at 18% 10%, rgba(47,109,246,0.16), transparent 30%), radial-gradient(circle at 88% 70%, rgba(15,118,110,0.12), transparent 28%)` }} />

      <div style={{ position: 'relative', zIndex: 2, display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 660px', gap: 54, padding: '78px 84px', height: '100%' }}>
        <div style={{ alignSelf: 'center', minWidth: 0, height: 850, border: `1px solid ${COLORS.borderSoft}`, background: '#ffffff', boxShadow: '0 30px 70px rgba(16,32,51,0.18)', overflow: 'hidden', opacity: spring({ frame: frame - 10, fps }), transform: `translateY(${(1 - spring({ frame: frame - 10, fps })) * 46}px)` }}>
          <Img src={staticFile("/screenshots/model-hero.png")} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 12, width: 'fit-content', minHeight: 36, padding: '7px 13px', border: `1px solid rgba(47,109,246,0.28)`, color: COLORS.modelTeal, fontFamily: '"JetBrains Mono", monospace', fontWeight: 700, fontSize: 20, textTransform: 'uppercase', opacity: interpolate(frame - 5, [0, 12], [0, 1], { extrapolateRight: 'clamp' }) }}>
            SYNTHETIC MARKET DATA ENGINE
          </div>
          <h2 style={{ margin: 0, fontWeight: 900, fontSize: 82, lineHeight: 0.94, color: COLORS.textDark, opacity: spring({ frame: frame - 10, fps }) }}>
            第二层，是 PT 重尾合成数据。
          </h2>
          <p style={{ margin: 0, maxWidth: 660, fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 35, lineHeight: 1.38, color: '#334155', opacity: interpolate(frame - 16, [0, 12], [0, 1], { extrapolateRight: 'clamp' }) }}>
            它不改变客户原策略，而是交付一层更重视极端行情的 OHLCV 数据底座。
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 14 }}>
            <div style={{ minWidth: 156, padding: '18px 20px', border: `1px solid #d9e3ef`, background: 'rgba(255,255,255,0.92)', opacity: interpolate(frame - 28, [0, 12], [0, 1], { extrapolateRight: 'clamp' }) }}>
              <small style={{ display: 'block', marginBottom: 8, color: '#64748b', fontFamily: '"JetBrains Mono", monospace', fontWeight: 700, fontSize: 18 }}>FIELDS</small>
              <strong style={{ display: 'block', fontFamily: 'Inter, sans-serif', fontWeight: 900, fontSize: 44, color: COLORS.modelTeal }}>pt_ohlcv</strong>
            </div>
            <div style={{ minWidth: 156, padding: '18px 20px', border: `1px solid #d9e3ef`, background: 'rgba(255,255,255,0.92)', opacity: interpolate(frame - 33, [0, 12], [0, 1], { extrapolateRight: 'clamp' }) }}>
              <small style={{ display: 'block', marginBottom: 8, color: '#64748b', fontFamily: '"JetBrains Mono", monospace', fontWeight: 700, fontSize: 18 }}>METHOD</small>
              <strong style={{ display: 'block', fontFamily: 'Inter, sans-serif', fontWeight: 900, fontSize: 44, color: COLORS.modelTeal }}>重尾先验</strong>
            </div>
          </div>
        </div>
      </div>
      <div style={{ position: 'absolute', left: 84, right: 84, bottom: 46, zIndex: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 28, minHeight: 70, padding: '16px 24px', border: `1px solid ${COLORS.borderSoft}`, background: 'rgba(255,255,255,0.9)', color: COLORS.textDark, opacity: interpolate(frame - 30, [0, 18], [0, 1], { extrapolateRight: 'clamp' }) }}>
        <span style={{ fontFamily: 'Inter, "PingFang SC", sans-serif', fontWeight: 700, fontSize: 32 }}>我们卖的不是单一策略，而是可接入现有流程的合成行情数据。</span>
        <code style={{ flexShrink: 0, color: COLORS.primaryBlue, fontWeight: 800, fontSize: 22, fontFamily: '"JetBrains Mono", monospace' }}>01:15</code>
      </div>
    </div>
  );
};

export const Scene7_ModelProof: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const delay = 27;

  const markets = [
    { name: 'A股', desc: '年化改善 14.91%，夏普改善 0.329', val: '+52.89%' },
    { name: '美股', desc: '年化改善 25.73%，夏普改善 0.428', val: '+148.88%' },
    { name: '港股', desc: '年化改善 20.79%，回撤改善 11.12%', val: '+152.75%' },
    { name: '加密货币', desc: '年化改善 52.96%，回撤改善 11.26%', val: '+671.76%' },
  ];

  return (
    <div style={{ position: 'absolute', inset: 0, background: COLORS.contentSurface }}>
      <div style={{ position: 'absolute', inset: 0, opacity: 0.42, backgroundImage: `linear-gradient(rgba(16,32,51,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(16,32,51,0.08) 1px, transparent 1px)`, backgroundSize: '80px 80px' }} />

      <div style={{ position: 'relative', zIndex: 2, display: 'grid', gridTemplateColumns: '690px minmax(0, 1fr)', gap: 54, padding: '78px 84px', height: '100%' }}>
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 12, width: 'fit-content', minHeight: 36, padding: '7px 13px', border: `1px solid rgba(47,109,246,0.28)`, color: COLORS.modelTeal, fontFamily: '"JetBrains Mono", monospace', fontWeight: 700, fontSize: 20, textTransform: 'uppercase', opacity: interpolate(frame - 5, [0, 12], [0, 1], { extrapolateRight: 'clamp' }) }}>
            MODEL PROOF
          </div>
          <h2 style={{ margin: 0, fontWeight: 900, fontSize: 82, lineHeight: 0.94, color: COLORS.textDark, opacity: spring({ frame: frame - 10, fps }) }}>
            四个市场，整体增强。
          </h2>
          <p style={{ margin: 0, maxWidth: 660, fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 35, lineHeight: 1.38, color: '#334155', opacity: interpolate(frame - 16, [0, 12], [0, 1], { extrapolateRight: 'clamp' }) }}>
            模型总览显示：4 个市场、16,944 个成功标的、163 组参数搜索；各市场平均收益改善均为正。
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 14, maxWidth: 690 }}>
            {[{ l: 'MARKETS', v: '4' }, { l: 'STOCKS', v: '16,944' }, { l: 'GRID', v: '163' }].map((item, i) => (
              <div key={i} style={{ minWidth: 156, padding: '18px 20px', border: `1px solid ${COLORS.borderSoft}`, background: 'rgba(255,255,255,0.92)', opacity: interpolate(frame - (25 + i * 5), [0, 12], [0, 1], { extrapolateRight: 'clamp' }) }}>
                <small style={{ display: 'block', marginBottom: 8, color: '#64748b', fontFamily: '"JetBrains Mono", monospace', fontWeight: 700, fontSize: 18 }}>{item.l}</small>
                <strong style={{ display: 'block', fontFamily: 'Inter, sans-serif', fontWeight: 900, fontSize: 44, color: COLORS.modelTeal }}>{item.v}</strong>
              </div>
            ))}
          </div>
        </div>

        <div style={{ alignSelf: 'center', display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 20, opacity: spring({ frame: frame - 14, fps }) }}>
          {markets.map((m, i) => {
            const d = delay + i * 8;
            const op = interpolate(frame - d, [0, 12], [0, 1], { extrapolateRight: 'clamp' });
            const y = interpolate(frame - d, [0, 12], [32, 0], { extrapolateRight: 'clamp' });
            return (
              <article key={i} style={{ minHeight: 178, padding: 24, border: `1px solid ${COLORS.borderSoft}`, background: 'rgba(255,255,255,0.92)', opacity: op, transform: `translateY(${y}px)` }}>
                <b style={{ display: 'block', marginBottom: 12, fontSize: 34, lineHeight: 1.05 }}>{m.name}</b>
                <p style={{ color: '#475569', fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 24, lineHeight: 1.32, margin: 0 }}>{m.desc}</p>
                <strong style={{ display: 'block', marginTop: 10, fontFamily: 'Inter, sans-serif', fontWeight: 900, fontSize: 58, color: COLORS.modelTeal }}>{m.val}</strong>
              </article>
            );
          })}
        </div>
      </div>

      <div style={{ position: 'absolute', left: 84, right: 84, bottom: 46, zIndex: 10, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 28, minHeight: 70, padding: '16px 24px', border: `1px solid ${COLORS.borderSoft}`, background: 'rgba(255,255,255,0.9)', color: COLORS.textDark, opacity: interpolate(frame - 30, [0, 18], [0, 1], { extrapolateRight: 'clamp' }) }}>
        <span style={{ fontFamily: 'Inter, "PingFang SC", sans-serif', fontWeight: 700, fontSize: 32 }}>这里的提升来自模型页真实显示的市场级验证数据。</span>
        <code style={{ flexShrink: 0, color: COLORS.primaryBlue, fontWeight: 800, fontSize: 22, fontFamily: '"JetBrains Mono", monospace' }}>01:30</code>
      </div>
    </div>
  );
};

export const Scene8_StrategyTest: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ position: 'absolute', inset: 0, background: COLORS.labSurface }}>
      <div style={{ position: 'absolute', inset: 0, opacity: 0.3, backgroundImage: `linear-gradient(rgba(82,215,247,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(82,215,247,0.08) 1px, transparent 1px)`, backgroundSize: '80px 80px' }} />
      <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(circle at 70% 50%, rgba(225,29,72,0.12), transparent 30%)`, opacity: 0.92 }} />

      <div style={{ position: 'relative', zIndex: 2, display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 660px', gap: 54, padding: '78px 84px', height: '100%' }}>
        <div style={{ alignSelf: 'center', display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 24, opacity: spring({ frame: frame - 14, fps }) }}>
          <div style={{ height: 700, border: '1px solid rgba(255,255,255,0.18)', background: 'rgba(7,12,22,0.84)', overflow: 'hidden', boxShadow: '0 32px 80px rgba(0,0,0,0.42)' }}>
            <Img src={staticFile("/screenshots/strategy-initial.png")} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'left top' }} />
          </div>
          <div style={{ height: 700, border: '1px solid rgba(255,255,255,0.18)', background: 'rgba(7,12,22,0.84)', overflow: 'hidden', boxShadow: '0 32px 80px rgba(0,0,0,0.42)' }}>
            <Img src={staticFile("/screenshots/strategy-loading.png")} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'left top' }} />
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24 }}>
          <Kicker text="RUN BACKTEST" delay={5} />
          <h2 style={{ margin: 0, fontWeight: 900, fontSize: 82, lineHeight: 0.94, color: '#f8fbff', opacity: spring({ frame: frame - 10, fps }) }}>
            同一只股票，同一套策略。
          </h2>
          <p style={{ margin: 0, maxWidth: 660, fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 35, lineHeight: 1.38, color: '#d8e5f3', opacity: interpolate(frame - 16, [0, 12], [0, 1], { extrapolateRight: 'clamp' }) }}>
            点击运行后，系统并排计算普通 5-20 均线和量子 5-20 均线，让提升效果可以直接对比。
          </p>
        </div>
      </div>
      <Caption text="策略页真实点击了运行，并抓取了计算中状态。" timestamp="01:45" startFrame={30} />
    </div>
  );
};

export const Scene9_StrategyResult: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <div style={{ position: 'absolute', inset: 0, background: COLORS.labSurface }}>
      <div style={{ position: 'absolute', inset: 0, opacity: 0.3, backgroundImage: `linear-gradient(rgba(82,215,247,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(82,215,247,0.08) 1px, transparent 1px)`, backgroundSize: '80px 80px' }} />

      <div style={{ position: 'relative', zIndex: 2, display: 'grid', gridTemplateColumns: '690px minmax(0, 1fr)', gap: 54, padding: '78px 84px', height: '100%' }}>
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 24 }}>
          <Kicker text="RESULT: 688027.SS" delay={5} />
          <h2 style={{ margin: 0, fontWeight: 900, fontSize: 82, lineHeight: 0.94, color: '#f8fbff', opacity: spring({ frame: frame - 10, fps }) }}>
            国盾量子，收益曲线被重新拉开。
          </h2>
          <p style={{ margin: 0, maxWidth: 660, fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 35, lineHeight: 1.38, color: '#d8e5f3', opacity: interpolate(frame - 16, [0, 12], [0, 1], { extrapolateRight: 'clamp' }) }}>
            普通 5-20 累计收益 275.08%；量子 5-20 达到 486.55%。
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 20, maxWidth: 690 }}>
            <article style={{ minHeight: 178, padding: 24, border: `1px solid rgba(82,215,247,0.26)`, background: 'rgba(8,15,28,0.74)', opacity: interpolate(frame - 27, [0, 12], [0, 1], { extrapolateRight: 'clamp' }) }}>
              <b style={{ display: 'block', marginBottom: 12, fontSize: 34, color: '#f8fbff' }}>5-20 均线</b>
              <p style={{ margin: 0, color: '#bfd1e6', fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 24 }}>累计收益率</p>
              <strong style={{ display: 'block', marginTop: 10, fontFamily: 'Inter, sans-serif', fontWeight: 900, fontSize: 58, color: COLORS.cyanSignal }}>275.08%</strong>
            </article>
            <article style={{
              minHeight: 178, padding: 24,
              border: `1px solid rgba(225,29,72,0.48)`,
              background: 'rgba(225,29,72,0.13)',
              opacity: interpolate(frame - 32, [0, 12], [0, 1], { extrapolateRight: 'clamp' }),
              transform: `scale(${1 + Math.sin(frame * 0.05) * 0.03})`,
            }}>
              <b style={{ display: 'block', marginBottom: 12, fontSize: 34, color: '#f8fbff' }}>量子 5-20</b>
              <p style={{ margin: 0, color: '#bfd1e6', fontFamily: 'Inter, sans-serif', fontWeight: 500, fontSize: 24 }}>累计收益率</p>
              <strong style={{ display: 'block', marginTop: 10, fontFamily: 'Inter, sans-serif', fontWeight: 900, fontSize: 58, color: COLORS.quantumRose }}>486.55%</strong>
            </article>
          </div>
        </div>

        <div style={{ alignSelf: 'center', minWidth: 0, height: 790, border: '1px solid rgba(255,255,255,0.18)', background: 'rgba(7,12,22,0.84)', boxShadow: '0 32px 80px rgba(0,0,0,0.42)', overflow: 'hidden', opacity: spring({ frame: frame - 14, fps }), transform: `translateY(${(1 - spring({ frame: frame - 14, fps })) * 46}px)` }}>
          <Img src={staticFile("/screenshots/strategy-result.png")} style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: 'left top' }} />
        </div>
      </div>
      <Caption text="合成数据路径让同一套策略的收益表现出现明显提升。" timestamp="02:00" startFrame={30} />
    </div>
  );
};
