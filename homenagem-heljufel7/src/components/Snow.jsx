import { Particles, ParticlesProvider } from "@tsparticles/react";
import { loadSlim } from "@tsparticles/slim";

// Fora do componente: o Particles recarrega sempre que a referência de options muda.
const particlesOptions = {
  background: {
    color: {
      value: "transparent",
    },
  },
  fpsLimit: 120,
  interactivity: {
    events: {
      onClick: {
        enable: false,
      },
      onHover: {
        enable: false,
      },
      resize: {
        enable: true,
      },
    },
  },
  particles: {
    color: {
      value: "#ffffff",
    },
    move: {
      direction: "bottom",
      enable: true,
      outModes: {
        default: "out",
      },
      random: true,
      speed: 2,
      straight: false,
    },
    number: {
      density: {
        enable: true,
        width: 800,
        height: 800,
      },
      value: 100,
    },
    opacity: {
      value: { min: 0.2, max: 0.6 },
    },
    shape: {
      type: "circle",
    },
    size: {
      value: { min: 1, max: 4 },
    },
  },
  detectRetina: true,
};

export default function Snow() {
  return (
    <ParticlesProvider init={loadSlim}>
      <Particles
        id="tsparticles"
        options={particlesOptions}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          zIndex: 0,
          pointerEvents: "none",
        }}
      />
    </ParticlesProvider>
  );
}
