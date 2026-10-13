/** home view. Hooks, requests and playback remain owned by RolePlayApp. */
import {
  CharacterAvatar,
  CommunityShowcase,
  MarketCard,
} from "../CharacterCards";
import type { HomeSection, Room } from "../types";

export type HomeViewProps = {
  openRoomWizard: (preselected?: string[]) => void;
  systemHomeCharacters: {
    creator: { id: string; name: string };
    id: string;
    name: string;
    display_name: string;
    description: string;
    initial_greeting?: string | undefined;
    tts_volume?: number | undefined;
    tts_voice_id?: string | undefined;
    tts_voice_mode?: "shared" | "separate" | undefined;
    tts_languages?:
      | Record<string, { enabled: boolean; voice_id: string }>
      | undefined;
    tts_voice_vi?: string | undefined;
    tts_voice_en?: string | undefined;
    tts_gender?: string | undefined;
    creation_type: string;
    simulation_label: boolean;
    preset_type?: string | undefined;
    category?: "utility" | "entertainment" | undefined;
    avatar_url?: string | undefined;
    is_public?: boolean | undefined;
    character_type?: string | undefined;
    tags?: string[] | undefined;
    rating?: number | undefined;
    rating_count?: number | undefined;
    usage_count?: number | undefined;
    trending_score?: number | undefined;
    home_section?:
      | "hidden"
      | "auto"
      | "featured"
      | "popular"
      | "top_rated"
      | undefined;
    reactions?: Record<string, number> | undefined;
    identity?: { role?: string | undefined } | undefined;
    support?:
      | {
          primary_role: "study" | "work" | "health" | "lifestyle" | "companion";
          strengths: (
            | "study"
            | "work"
            | "health"
            | "lifestyle"
            | "companion"
          )[];
          introduction: string;
        }
      | undefined;
  }[];
  introText: (value: string) => string;
  addPreset: (p: import("../types").Character) => Promise<void>;
  customHomeCharacters: {
    creator:
      | { id: string; name: string; followers?: number | undefined }
      | undefined;
    id: string;
    name: string;
    display_name: string;
    description: string;
    initial_greeting?: string | undefined;
    tts_volume?: number | undefined;
    tts_voice_id?: string | undefined;
    tts_voice_mode?: "shared" | "separate" | undefined;
    tts_languages?:
      | Record<string, { enabled: boolean; voice_id: string }>
      | undefined;
    tts_voice_vi?: string | undefined;
    tts_voice_en?: string | undefined;
    tts_gender?: string | undefined;
    creation_type: string;
    simulation_label: boolean;
    preset_type?: string | undefined;
    category?: "utility" | "entertainment" | undefined;
    avatar_url?: string | undefined;
    is_public?: boolean | undefined;
    character_type?: string | undefined;
    tags?: string[] | undefined;
    rating?: number | undefined;
    rating_count?: number | undefined;
    usage_count?: number | undefined;
    trending_score?: number | undefined;
    home_section?:
      | "hidden"
      | "auto"
      | "featured"
      | "popular"
      | "top_rated"
      | undefined;
    reactions?: Record<string, number> | undefined;
    identity?: { role?: string | undefined } | undefined;
    support?:
      | {
          primary_role: "study" | "work" | "health" | "lifestyle" | "companion";
          strengths: (
            | "study"
            | "work"
            | "health"
            | "lifestyle"
            | "companion"
          )[];
          introduction: string;
        }
      | undefined;
  }[];
  startCharacterChat: (
    character: import("../types").Character,
  ) => Promise<void>;
  homeSections: HomeSection[];
  charactersForSection: (
    section: HomeSection,
  ) => (
    | import("../types").Character
    | {
        creator: { id: string; name: string };
        id: string;
        name: string;
        display_name: string;
        description: string;
        initial_greeting?: string | undefined;
        tts_volume?: number | undefined;
        tts_voice_id?: string | undefined;
        tts_voice_mode?: "shared" | "separate" | undefined;
        tts_languages?:
          | Record<string, { enabled: boolean; voice_id: string }>
          | undefined;
        tts_voice_vi?: string | undefined;
        tts_voice_en?: string | undefined;
        tts_gender?: string | undefined;
        creation_type: string;
        simulation_label: boolean;
        preset_type?: string | undefined;
        category?: "utility" | "entertainment" | undefined;
        avatar_url?: string | undefined;
        is_public?: boolean | undefined;
        character_type?: string | undefined;
        tags?: string[] | undefined;
        rating?: number | undefined;
        rating_count?: number | undefined;
        usage_count?: number | undefined;
        trending_score?: number | undefined;
        home_section?:
          | "hidden"
          | "auto"
          | "featured"
          | "popular"
          | "top_rated"
          | undefined;
        reactions?: Record<string, number> | undefined;
        identity?: { role?: string | undefined } | undefined;
        support?:
          | {
              primary_role:
                | "study"
                | "work"
                | "health"
                | "lifestyle"
                | "companion";
              strengths: (
                | "study"
                | "work"
                | "health"
                | "lifestyle"
                | "companion"
              )[];
              introduction: string;
            }
          | undefined;
      }
  )[];
  startPublicCharacter: (
    character: import("../types").Character,
  ) => Promise<void>;
  visibleRooms: Room[];
  matchesSearch: (...values: (string | undefined)[]) => boolean;
  openRoom: (r: Room) => Promise<void>;
};

export function renderHomeView(props: HomeViewProps) {
  const {
    openRoomWizard,
    systemHomeCharacters,
    introText,
    addPreset,
    customHomeCharacters,
    startCharacterChat,
    homeSections,
    charactersForSection,
    startPublicCharacter,
    visibleRooms,
    matchesSearch,
    openRoom,
  } = props;
  return (
    <>
      <header>
        <span className="eyebrow">KHÁM PHÁ NHÂN VẬT</span>

        <h1>Hôm nay bạn cần ai đồng hành?</h1>

        <p>
          Chọn một người phù hợp với tâm trạng, học tập hoặc công việc của bạn.
        </p>
      </header>

      <div className="actions">
        <button className="secondaryButton" onClick={() => openRoomWizard()}>
          Tạo phòng nhóm
        </button>
      </div>

      {!!systemHomeCharacters.length && (
        <section className="systemCharacterLane">
          <div className="laneHeading">
            <h2>Nhân vật hệ thống</h2>

            <span> </span>
          </div>

          <div className="marketRow">
            {systemHomeCharacters.map((character) => (
              <MarketCard
                key={character.id}
                introduction={introText(character.description)}
                character={character}
                onOpen={() => addPreset(character)}
              />
            ))}
          </div>
        </section>
      )}

      {!!customHomeCharacters.length && (
        <section className="largeCharacterSection">
          <div className="laneHeading">
            <h2>Nhân vật của bạn</h2>

            <span> </span>
          </div>

          <div className="grid showcaseGrid">
            {customHomeCharacters.map((character) => (
              <button
                className="card characterIntro showcaseCard"
                key={character.id}
                onClick={() => startCharacterChat(character)}
              >
                <CharacterAvatar
                  character={character}
                  className="showcaseImage"
                />

                <div className="showcaseCopy">
                  <span className="roleBadge companion">
                    {character.character_type || "Custom"}
                  </span>

                  <strong data-no-translate="true" translate="no">
                    {character.name}
                  </strong>

                  <h3 data-no-translate="true" translate="no">
                    {character.display_name || character.name}
                  </h3>

                  <p data-no-translate="true" translate="no">
                    {introText(character.description)}
                  </p>

                  <span className="showcaseMeta">
                    ◉ {character.usage_count || 0} người dùng{" "}
                    <b>Trò chuyện →</b>
                  </span>
                </div>
              </button>
            ))}
          </div>
        </section>
      )}

      {homeSections.map((section) => {
        const members = charactersForSection(section);
        if (!members.length) return null;
        return (
          <section className="largeCharacterSection" key={section.id}>
            <div className="laneHeading">
              <h2>{section.name}</h2>

              <span></span>
            </div>

            <div className="grid showcaseGrid">
              {members.map((character) => (
                <CommunityShowcase
                  introduction={introText(character.description)}
                  key={`${section.id}:${character.id}`}
                  character={character}
                  onOpen={() =>
                    character.creation_type === "preset"
                      ? addPreset(character)
                      : startPublicCharacter(character)
                  }
                />
              ))}
            </div>
          </section>
        );
      })}

      <h2>Tiếp tục trò chuyện</h2>

      <div className="grid">
        {visibleRooms
          .filter((r) => matchesSearch(r.name))
          .map((r) => (
            <button
              className="card"
              key={r.id}
              onClick={() => {
                void openRoom(r).catch(() => {});
              }}
            >
              {r.name}
            </button>
          ))}
      </div>
    </>
  );
}
