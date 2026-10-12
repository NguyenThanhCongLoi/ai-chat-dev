/** home view. Hooks, requests and playback remain owned by RolePlayApp. */
import { BackgroundMusicButton } from "../BackgroundMusicButton";

export type HomeBackdropViewProps = {
  backgroundMusic: {
    enabled: boolean;
    playing: boolean;
    loading: boolean;
    available: boolean;
    error: boolean;
    volume: number;
    changeVolume: (value: number) => void;
    toggle: () => void;
  };
};

export function renderHomeBackdropView(props: HomeBackdropViewProps) {
  const { backgroundMusic } = props;
  return (
    <div className="rpBackgroundMusicFloating">
      <BackgroundMusicButton {...backgroundMusic} />
    </div>
  );
}
