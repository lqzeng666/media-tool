"""Video generation using Remotion (React-based video framework).

Sets up a Remotion project from the presentation outline and renders to MP4.
Follows remotion-dev/skills best practices.
"""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from core.content_structurer import PresentationOutline

logger = logging.getLogger(__name__)

REMOTION_DIR = Path("output/remotion-project")


def _ensure_remotion_project() -> Path:
    """Initialize the Remotion project if it doesn't exist."""
    project_dir = REMOTION_DIR
    if (project_dir / "package.json").exists():
        return project_dir

    project_dir.mkdir(parents=True, exist_ok=True)

    # package.json
    pkg = {
        "name": "media-video",
        "version": "1.0.0",
        "private": True,
        "scripts": {
            "dev": "remotion studio",
            "render": "remotion render src/index.tsx MainComposition output/video.mp4",
        },
        "dependencies": {
            "@remotion/cli": "^4.0.0",
            "react": "^18.0.0",
            "react-dom": "^18.0.0",
            "remotion": "^4.0.0",
        },
        "devDependencies": {
            "typescript": "^5.0.0",
            "@types/react": "^18.0.0",
        },
    }
    (project_dir / "package.json").write_text(json.dumps(pkg, indent=2))

    # tsconfig.json
    tsconfig = {
        "compilerOptions": {
            "target": "ES2018",
            "module": "commonjs",
            "jsx": "react-jsx",
            "strict": True,
            "esModuleInterop": True,
            "outDir": "./dist",
        },
        "include": ["src"],
    }
    (project_dir / "tsconfig.json").write_text(json.dumps(tsconfig, indent=2))

    # src directory
    src = project_dir / "src"
    src.mkdir(exist_ok=True)

    # Root index
    (src / "index.tsx").write_text("""\
import {registerRoot} from 'remotion';
import {RemotionRoot} from './Root';

registerRoot(RemotionRoot);
""")

    # Root component
    (src / "Root.tsx").write_text("""\
import {Composition} from 'remotion';
import {MainComposition} from './Composition';
import data from './data.json';

export const RemotionRoot: React.FC = () => {
  const durationPerSlide = 150; // 5 seconds at 30fps
  const totalDuration = (data.sections.length + 2) * durationPerSlide;

  return (
    <Composition
      id="MainComposition"
      component={MainComposition}
      durationInFrames={totalDuration}
      fps={30}
      width={1280}
      height={720}
      defaultProps={{data}}
    />
  );
};
""")

    # Main composition
    (src / "Composition.tsx").write_text("""\
import {AbsoluteFill, Sequence, useCurrentFrame, interpolate, spring, useVideoConfig} from 'remotion';

interface Section {
  title: string;
  bullets: string[];
}

interface OutlineData {
  title: string;
  subtitle: string;
  sections: Section[];
}

const SLIDE_DURATION = 150; // 5s at 30fps

const TitleSlide: React.FC<{title: string; subtitle: string}> = ({title, subtitle}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const opacity = interpolate(frame, [0, 20], [0, 1], {extrapolateRight: 'clamp'});
  const titleY = spring({frame, fps, from: 30, to: 0, durationInFrames: 30});

  return (
    <AbsoluteFill style={{
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)',
      display: 'flex', flexDirection: 'column', justifyContent: 'center',
      padding: '60px 80px', color: 'white', opacity,
    }}>
      <div style={{width: 120, height: 4, background: '#00d2ff', marginBottom: 24}} />
      <h1 style={{fontSize: 48, fontWeight: 700, transform: `translateY(${titleY}px)`, fontFamily: 'PingFang SC, sans-serif'}}>
        {title}
      </h1>
      <p style={{fontSize: 22, color: '#aaa', marginTop: 16, fontFamily: 'PingFang SC, sans-serif'}}>
        {subtitle}
      </p>
    </AbsoluteFill>
  );
};

const ContentSlide: React.FC<{index: number; title: string; bullets: string[]}> = ({index, title, bullets}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const opacity = interpolate(frame, [0, 15], [0, 1], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{
      background: 'linear-gradient(180deg, #16213e 0%, #1a1a2e 100%)',
      display: 'flex', flexDirection: 'column', justifyContent: 'center',
      padding: '60px 80px', color: 'white', opacity,
    }}>
      <div style={{fontSize: 14, color: '#00d2ff', fontWeight: 600, marginBottom: 12}}>
        {String(index).padStart(2, '0')}
      </div>
      <h2 style={{fontSize: 36, fontWeight: 700, marginBottom: 12, fontFamily: 'PingFang SC, sans-serif'}}>
        {title}
      </h2>
      <div style={{width: 80, height: 3, background: '#00d2ff', marginBottom: 32}} />
      {bullets.map((b, i) => {
        const delay = i * 10;
        const bOpacity = interpolate(frame, [delay + 15, delay + 30], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
        const bX = spring({frame: Math.max(0, frame - delay - 15), fps, from: 20, to: 0, durationInFrames: 20});
        return (
          <div key={i} style={{
            display: 'flex', alignItems: 'flex-start',
            marginBottom: 18, fontSize: 20, color: '#ccc',
            opacity: bOpacity, transform: `translateX(${bX}px)`,
            fontFamily: 'PingFang SC, sans-serif',
          }}>
            <span style={{color: '#00d2ff', marginRight: 16, fontSize: 12, marginTop: 6}}>●</span>
            <span>{b}</span>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

const EndSlide: React.FC = () => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 20], [0, 1], {extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill style={{
      background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
      display: 'flex', flexDirection: 'column', justifyContent: 'center',
      alignItems: 'center', color: 'white', opacity,
    }}>
      <h1 style={{fontSize: 48, fontFamily: 'PingFang SC, sans-serif'}}>谢谢观看</h1>
      <p style={{fontSize: 18, color: '#888', marginTop: 20, fontFamily: 'PingFang SC, sans-serif'}}>
        Generated by Media Tool
      </p>
    </AbsoluteFill>
  );
};

export const MainComposition: React.FC<{data: OutlineData}> = ({data}) => {
  return (
    <AbsoluteFill>
      <Sequence from={0} durationInFrames={SLIDE_DURATION}>
        <TitleSlide title={data.title} subtitle={data.subtitle} />
      </Sequence>
      {data.sections.map((sec, i) => (
        <Sequence key={i} from={(i + 1) * SLIDE_DURATION} durationInFrames={SLIDE_DURATION}>
          <ContentSlide index={i + 1} title={sec.title} bullets={sec.bullets} />
        </Sequence>
      ))}
      <Sequence from={(data.sections.length + 1) * SLIDE_DURATION} durationInFrames={SLIDE_DURATION}>
        <EndSlide />
      </Sequence>
    </AbsoluteFill>
  );
};
""")

    # Install dependencies
    logger.info("Installing Remotion dependencies...")
    subprocess.run(
        ["npm", "install"],
        cwd=str(project_dir),
        capture_output=True,
        timeout=120,
    )

    return project_dir


def write_outline_data(outline: PresentationOutline) -> Path:
    """Write outline data as JSON for Remotion to consume."""
    project_dir = _ensure_remotion_project()
    data_path = project_dir / "src" / "data.json"
    data = {
        "title": outline.title,
        "subtitle": outline.subtitle,
        "sections": [
            {"title": s.title, "bullets": s.bullets}
            for s in outline.sections
        ],
    }
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    return data_path


def render_video(outline: PresentationOutline, output_path: str = "output/video.mp4") -> Path:
    """Set up Remotion project with outline data and render to MP4."""
    project_dir = _ensure_remotion_project()
    write_outline_data(outline)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        ["npx", "remotion", "render", "src/index.tsx", "MainComposition", str(out.absolute())],
        cwd=str(project_dir),
        capture_output=True,
        text=True,
        timeout=300,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Remotion render failed: {result.stderr}")

    return out
