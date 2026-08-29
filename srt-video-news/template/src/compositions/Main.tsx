import { AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame } from "remotion";
import { designTokens, hostDecor } from "../design-system";
import { videoConfig } from "../video-config";
import { generatedScenes } from "./generated-scenes";

const msToFrames = (ms: number) => Math.round((ms / 1000) * videoConfig.fps);

export const Main: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: designTokens.background.host, overflow: "hidden" }}>
      {/* Audio */}
      <Audio src={staticFile("audio.mp3")} />

      <div
        style={{
          position: "absolute",
          width: videoConfig.designWidth,
          height: videoConfig.designHeight,
          transform: `scale(${videoConfig.stageScale})`,
          transformOrigin: "top left",
        }}
      >
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
            <Sequence
              key={index}
              name={`Scene${String(index + 1).padStart(3, "0")}`}
              from={fromFrame}
              durationInFrames={durationInFrames}
            >
              <Component segments={scene.segments} />
            </Sequence>
          );
        })}

        {/* Subtitles layer - shows current segment text */}
        <SubtitleOverlay />
      </div>
    </AbsoluteFill>
  );
};

const SubtitleOverlay: React.FC = () => {
  const frame = useCurrentFrame();
  const currentMs = Math.round((frame / videoConfig.fps) * 1000);

  // Find the current active scene and segment
  let currentText = "";

  for (const scene of generatedScenes) {
    const sceneEnd = scene.start + scene.duration;
    if (currentMs >= scene.start && currentMs < sceneEnd) {
      const relativeMs = currentMs - scene.start;
      // Find active segment
      let cumulativeMs = 0;
      for (const seg of scene.segments) {
        const segStart = seg.relativeStart;
        const segEnd = seg.relativeStart + seg.relativeDuration;
        if (relativeMs >= segStart && relativeMs < segEnd) {
          currentText = seg.text;
          break;
        }
      }
      break;
    }
  }

  if (!currentText) return null;

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        bottom: 80,
        width: "100%",
        display: "flex",
        justifyContent: "center",
        pointerEvents: "none",
        zIndex: 1000,
      }}
    >
      <div
        style={{
          maxWidth: "88%",
          textAlign: "center",
          fontSize: 50,
          fontWeight: 700,
          color: "#fff",
          lineHeight: 1.4,
          fontFamily: "'Noto Serif SC', serif",
          textShadow:
            "0 2px 6px rgba(0,0,0,.9), 0 0 18px rgba(0,0,0,.75), 0 0 40px rgba(0,0,0,.5), 0 0 60px rgba(196,30,36,.25)",
          background: "rgba(0,0,0,0.55)",
          borderRadius: 8,
          padding: "8px 24px",
        }}
      >
        {currentText}
      </div>
    </div>
  );
};
