import { AbsoluteFill, Sequence } from "remotion";
import { designTokens, hostDecor } from "../design-system";
import { videoConfig } from "../video-config";
import { generatedScenes } from "./generated-scenes";

const msToFrames = (ms: number) => Math.round((ms / 1000) * videoConfig.fps);

export const Main: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: designTokens.background.host, overflow: "hidden" }}>
      <div
        style={{
          position: "absolute",
          width: videoConfig.designWidth,
          height: videoConfig.designHeight,
          transform: `scale(${videoConfig.stageScale})`,
          transformOrigin: "top left",
        }}
      >
        {/* 极细点阵 - 国风纸张质感 */}
        <AbsoluteFill
          style={{
            backgroundImage: `radial-gradient(circle, ${designTokens.background.dots} 0.8px, transparent 0.8px)`,
            backgroundSize: hostDecor.dotSize,
            opacity: hostDecor.dotOpacity,
          }}
        />

        {/* 宣纸纹理叠加层 */}
        <AbsoluteFill
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='xuan'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='4'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3CfeComponentTransfer%3E%3CfeFuncA type='linear' slope='0.04'/%3E%3C/feComponentTransfer%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23xuan)' opacity='0.06'/%3E%3C/svg%3E")`,
            pointerEvents: "none",
          }}
        />

        {/* 场景序列 */}
        {generatedScenes.map((scene, index) => {
          const fromFrame = msToFrames(scene.start);

          let durationInFrames: number;
          if (index < generatedScenes.length - 1) {
            const nextStart = generatedScenes[index + 1].start;
            durationInFrames = msToFrames(nextStart - scene.start);
          } else {
            durationInFrames = msToFrames(scene.duration);
          }

          const Component = scene.Component;

          return (
            <Sequence key={index} name={`Scene${String(index + 1).padStart(3, '0')}`} from={fromFrame} durationInFrames={durationInFrames}>
              <Component segments={scene.segments} />
            </Sequence>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
