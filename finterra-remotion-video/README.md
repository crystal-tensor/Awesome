# FinTerra 宣传视频 — Remotion Project

## 项目结构

```
finterra-remotion-video/
├── src/
│   ├── index.ts              # 入口, registerRoot
│   ├── Root.tsx              # 主合成, 12 场景 + 双音频
│   ├── constants.tsx         # 品牌色, 尺寸, 字体
│   ├── Caption.tsx           # 字幕组件 (Caption, Kicker, ProofCard)
│   └── scenes/
│       ├── Scene1_Opening.tsx      # 0-15s  开场
│       ├── Scene2_OneWorkbench.tsx  # 15-30s  四大支柱
│       ├── Scene3_LiveIntelligence.tsx # 30-45s  实时图谱
│       ├── Scene4_ClickSend.tsx     # 45-60s  点击发送
│       ├── Scene5_GraphEffects.tsx  # 60-75s  图谱特效
│       ├── Scene6_9.tsx             # 75-135s 合成数据+模型证据+策略测试+策略结果
│       ├── Scene10_11.tsx           # 135-165s 风险质量+单股验证
│       └── Scene12_CTA.tsx          # 165-180s 收尾+行动号召
├── public/
│   ├── screenshots/          # 从实时网站捕获的屏幕截图
│   └── audio/                # narration.mp3 (中文普通话旁白) + bg_music.mp3
├── remotion.config.ts
├── tsconfig.json
└── package.json
```

## 技术规格

- **分辨率**: 1920×1080 (16:9)
- **帧率**: 30fps
- **总帧数**: 5400 (180秒)
- **每场景**: 450 帧 (15秒)

## 渲染命令

```bash
# 开发预览
npx remotion studio src/index.ts

# 导出 MP4
npx remotion render src/index.ts FinTerraPromo out/finterra-promo.mp4
```

## 品牌色

| 名称 | 色值 | 用途 |
|------|------|------|
| Lab Surface | #0b111c | 深色场景背景 |
| Content Surface | #f4f7fb | 浅色场景背景 |
| Cyan Signal | #52d7f7 | 图谱高亮/实时状态 |
| Quantum Rose | #e11d48 | PT/量子结果强调 |
| Model Teal | #0f766e | 模型证据/正向改善 |
| Primary Blue | #2f6df6 | 主按钮/选择控件 |

## 叙事结构

1. **强开场** (0-15s) — 金融决策的碎片化痛点
2. **工作台亮相** (15-30s) — 四大产品支柱
3. **实时资讯图谱** (30-60s) — 数据→关系→推演过程
4. **中间生成效果** (60-75s) — 2D/3D 视觉效果
5. **合成数据引擎** (75-105s) — PT 重尾数据 + 四市场证据
6. **策略验证** (105-150s) — 运行回测 → 收益 → 风险对比
7. **单股验证闭环** (150-165s) — 点击股票即时验证
8. **收尾 + CTA** (165-180s) — 品牌 + 证据链总结
