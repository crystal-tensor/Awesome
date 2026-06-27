import React from 'react';
import { Composition, Sequence, Audio } from 'remotion';
import { VIDEO_WIDTH, VIDEO_HEIGHT, TOTAL_DURATION, SCENE_DURATION } from './constants';
import { Scene1_Opening } from './scenes/Scene1_Opening';
import { Scene2_OneWorkbench } from './scenes/Scene2_OneWorkbench';
import { Scene3_LiveIntelligence } from './scenes/Scene3_LiveIntelligence';
import { Scene4_ClickSend } from './scenes/Scene4_ClickSend';
import { Scene5_GraphEffects } from './scenes/Scene5_GraphEffects';
import { Scene6_SyntheticData, Scene7_ModelProof, Scene8_StrategyTest, Scene9_StrategyResult } from './scenes/Scene6_9';
import { Scene10_RiskAdjusted, Scene11_SingleStock } from './scenes/Scene10_11';
import { Scene12_CTA } from './scenes/Scene12_CTA';

import narrationMp3 from '../public/audio/narration.mp3';
import bgMusicMp3 from '../public/audio/bg_music.mp3';

const FinTerraPromoVideo: React.FC = () => {
  return (
    <div style={{
      width: VIDEO_WIDTH,
      height: VIDEO_HEIGHT,
      background: '#0b111c',
      overflow: 'hidden',
      fontFamily: 'Inter, "PingFang SC", "Microsoft YaHei", sans-serif',
      WebkitFontSmoothing: 'antialiased',
    }}>
      <Audio src={bgMusicMp3} volume={0.25} />
      <Audio src={narrationMp3} volume={0.85} />
      <Sequence from={0 * SCENE_DURATION} durationInFrames={SCENE_DURATION} name="Opening">
        <Scene1_Opening />
      </Sequence>
      <Sequence from={1 * SCENE_DURATION} durationInFrames={SCENE_DURATION} name="One Workbench">
        <Scene2_OneWorkbench />
      </Sequence>
      <Sequence from={2 * SCENE_DURATION} durationInFrames={SCENE_DURATION} name="Live Intelligence">
        <Scene3_LiveIntelligence />
      </Sequence>
      <Sequence from={3 * SCENE_DURATION} durationInFrames={SCENE_DURATION} name="Click Send">
        <Scene4_ClickSend />
      </Sequence>
      <Sequence from={4 * SCENE_DURATION} durationInFrames={SCENE_DURATION} name="Graph Effects">
        <Scene5_GraphEffects />
      </Sequence>
      <Sequence from={5 * SCENE_DURATION} durationInFrames={SCENE_DURATION} name="Synthetic Data">
        <Scene6_SyntheticData />
      </Sequence>
      <Sequence from={6 * SCENE_DURATION} durationInFrames={SCENE_DURATION} name="Model Proof">
        <Scene7_ModelProof />
      </Sequence>
      <Sequence from={7 * SCENE_DURATION} durationInFrames={SCENE_DURATION} name="Strategy Test">
        <Scene8_StrategyTest />
      </Sequence>
      <Sequence from={8 * SCENE_DURATION} durationInFrames={SCENE_DURATION} name="Strategy Result">
        <Scene9_StrategyResult />
      </Sequence>
      <Sequence from={9 * SCENE_DURATION} durationInFrames={SCENE_DURATION} name="Risk Adjusted">
        <Scene10_RiskAdjusted />
      </Sequence>
      <Sequence from={10 * SCENE_DURATION} durationInFrames={SCENE_DURATION} name="Single Stock">
        <Scene11_SingleStock />
      </Sequence>
      <Sequence from={11 * SCENE_DURATION} durationInFrames={SCENE_DURATION} name="CTA">
        <Scene12_CTA />
      </Sequence>
    </div>
  );
};

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="FinTerraPromo"
        component={FinTerraPromoVideo}
        durationInFrames={TOTAL_DURATION}
        fps={30}
        width={VIDEO_WIDTH}
        height={VIDEO_HEIGHT}
      />
    </>
  );
};
