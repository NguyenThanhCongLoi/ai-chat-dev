/** settings view. Hooks, requests and playback remain owned by RolePlayApp. */
import type * as React from "react";
import { UI_LANGUAGES, type UiLanguage } from "../../i18n";
import { API } from "../api";
import type { Account } from "../types";

export type SettingsViewProps = {
  setSettingsOpen: React.Dispatch<React.SetStateAction<boolean>>;
  account: NonNullable<import("../types").Account>;
  settingsTab: "profile" | "account" | "preferences";
  setSettingsTab: React.Dispatch<
    React.SetStateAction<"profile" | "account" | "preferences">
  >;
  logout: () => Promise<void>;
  act: (
    f: () => Promise<void>,
    preparesResources?: boolean,
    successMessage?: string,
  ) => Promise<void>;
  uploadUserAvatar: (file: File) => Promise<void>;
  profileName: string;
  setProfileName: React.Dispatch<React.SetStateAction<string>>;
  profileBio: string;
  setProfileBio: React.Dispatch<React.SetStateAction<string>>;
  saveProfile: () => Promise<void>;
  currentPassword: string;
  setCurrentPassword: React.Dispatch<React.SetStateAction<string>>;
  newPassword: string;
  setNewPassword: React.Dispatch<React.SetStateAction<string>>;
  changePassword: () => Promise<void>;
  savePreferences: (
    values: Partial<import("../types").Account>,
  ) => Promise<void>;
};

export function renderSettingsView(props: SettingsViewProps) {
  const {
    setSettingsOpen,
    account,
    settingsTab,
    setSettingsTab,
    logout,
    act,
    uploadUserAvatar,
    profileName,
    setProfileName,
    profileBio,
    setProfileBio,
    saveProfile,
    currentPassword,
    setCurrentPassword,
    newPassword,
    setNewPassword,
    changePassword,
    savePreferences,
  } = props;
  return (
    <div
      className="settingsOverlay"
      onMouseDown={(e) =>
        e.target === e.currentTarget && setSettingsOpen(false)
      }
    >
      <section className="personalSettings">
        <aside className="settingsNav">
          <div className="settingsIdentity">
            {account.avatar_url ? (
              <img src={API + account.avatar_url} alt="Avatar" />
            ) : (
              <span>{account.display_name[0]?.toUpperCase()}</span>
            )}

            <b>{account.display_name}</b>

            <small>@{account.username}</small>
          </div>

          <button
            className={settingsTab === "profile" ? "active" : ""}
            onClick={() => setSettingsTab("profile")}
          >
            Hồ sơ công khai
          </button>

          <button
            className={settingsTab === "account" ? "active" : ""}
            onClick={() => setSettingsTab("account")}
          >
            Tài khoản
          </button>

          <button
            className={settingsTab === "preferences" ? "active" : ""}
            onClick={() => setSettingsTab("preferences")}
          >
            Tùy chọn
          </button>

          <button className="settingsLogout" onClick={logout}>
            Đăng xuất
          </button>
        </aside>

        <div className="settingsContent">
          <button
            className="settingsClose"
            onClick={() => setSettingsOpen(false)}
          >
            ×
          </button>

          {settingsTab === "profile" && (
            <>
              <h2>Hồ sơ công khai</h2>

              <label className="profileAvatar">
                {account.avatar_url ? (
                  <img src={API + account.avatar_url} alt="Avatar" />
                ) : (
                  <span>{account.display_name[0]?.toUpperCase()}</span>
                )}

                <b>Thay avatar</b>

                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/gif"
                  onChange={(e) =>
                    e.target.files?.[0] &&
                    act(() => uploadUserAvatar(e.target.files![0]))
                  }
                />
              </label>

              <label>
                Tên đăng nhập
                <input value={account.username} disabled />
              </label>

              <label>
                Tên hiển thị
                <input
                  maxLength={80}
                  value={profileName}
                  onChange={(e) => setProfileName(e.target.value)}
                />
              </label>

              <label>
                Giới thiệu
                <textarea
                  maxLength={500}
                  value={profileBio}
                  onChange={(e) => setProfileBio(e.target.value)}
                  placeholder="Giới thiệu ngắn về bạn…"
                />
              </label>

              <button onClick={() => act(saveProfile)}>Lưu hồ sơ</button>
            </>
          )}

          {settingsTab === "account" && (
            <>
              <h2>Tài khoản</h2>

              <div className="accountSummary">
                <span>Gói hiện tại</span>

                <b>Demo</b>
              </div>

              <label>
                Mật khẩu hiện tại
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                />
              </label>

              <label>
                Mật khẩu mới
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Ít nhất 6 ký tự"
                />
              </label>

              <button
                disabled={!currentPassword || newPassword.length < 6}
                onClick={() => act(changePassword)}
              >
                Đổi mật khẩu
              </button>
            </>
          )}

          {settingsTab === "preferences" && (
            <>
              <h2>Tùy chọn</h2>

              <label>
                Giao diện
                <select
                  value={account.theme}
                  onChange={(e) =>
                    savePreferences({
                      theme: e.target.value as Account["theme"],
                    })
                  }
                >
                  <option value="light">Sáng</option>

                  <option value="dark">Tối</option>
                </select>
              </label>

              <label>
                Ngôn ngữ
                <select
                  value={account.language}
                  onChange={(e) =>
                    savePreferences({
                      language: e.target.value as UiLanguage,
                    })
                  }
                >
                  {UI_LANGUAGES.map((language) => (
                    <option value={language.code} key={language.code}>
                      {language.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="preferenceToggle">
                <span>
                  <b>Giảm chuyển động</b>

                  <small>Hạn chế animation trong giao diện.</small>
                </span>

                <input
                  type="checkbox"
                  checked={account.reduced_motion}
                  onChange={(e) =>
                    savePreferences({ reduced_motion: e.target.checked })
                  }
                />
              </label>
            </>
          )}
        </div>
      </section>
    </div>
  );
}
