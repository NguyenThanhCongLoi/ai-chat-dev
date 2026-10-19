// CMS composition: shared state + typed runtime + original DOM event wiring.
// Feature handlers live in admin/controllers/; getters keep async saves in sync.
import "./admin-styles.css";
import { renderActionSounds } from "./admin/actionSounds";
import { createAccessController } from "./admin/controllers/access";
import { createAssignmentsController } from "./admin/controllers/assignments";
import { createAssistantsController } from "./admin/controllers/assistants";
import { createBootstrapController } from "./admin/controllers/bootstrap";
import { createCharactersController } from "./admin/controllers/characters";
import { createDashboardController } from "./admin/controllers/dashboard";
import { createDatabaseController } from "./admin/controllers/database";
import { createHomeSectionsController } from "./admin/controllers/homeSections";
import { createLogsController } from "./admin/controllers/logs";
import { createModelsController } from "./admin/controllers/models";
import { createPresentationController } from "./admin/controllers/presentation";
import { createCmsLogViews } from "./admin/logs";
import { renderBackgroundMusic } from "./admin/music";
import type {
  AccessControl,
  AdminCharacter,
  AssistantDraft,
  AssistantProfile,
  AssistantProfiles,
  AssistantTab,
  CharacterCatalog,
  CmsHomeSection,
  Connection,
  CredentialState,
  DbTable,
  GlobalDraft,
  LogRow,
  ModelConfig,
  ModelUpdate,
  NewAssistantForm,
  Overview,
  Settings,
} from "./admin/types";

/** Shared CMS state and callbacks; getters prevent stale snapshots after saves. */
export type AdminRuntime = {
  ACTION_GROUPS: typeof ACTION_GROUPS;
  ACTION_STATUS: typeof ACTION_STATUS;
  ASSIGN_TASKS: typeof ASSIGN_TASKS;
  ASSISTANT_HUES: typeof ASSISTANT_HUES;
  ASSISTANT_ICONS: typeof ASSISTANT_ICONS;
  CREATE_FIELDS: typeof CREATE_FIELDS;
  EDIT_FIELDS: typeof EDIT_FIELDS;
  GATEWAY_BASE: typeof GATEWAY_BASE;
  LOGCHAT_PAGE_SIZE: typeof LOGCHAT_PAGE_SIZE;
  PRODUCT_LABELS: typeof PRODUCT_LABELS;
  ROLE_LABELS: typeof ROLE_LABELS;
  SECTION_RULES: typeof SECTION_RULES;
  SECTION_RULE_HINTS: typeof SECTION_RULE_HINTS;
  accessControl: typeof accessControl;
  actionColumns: typeof actionColumns;
  actionRows: typeof actionRows;
  activeAssistantPurpose: typeof activeAssistantPurpose;
  activeAssistantTab: typeof activeAssistantTab;
  activeDbTable: typeof activeDbTable;
  addModel: typeof addModel;
  adminCharacters: typeof adminCharacters;
  assignmentState: typeof assignmentState;
  assignmentValue: typeof assignmentValue;
  assistantCardPreview: typeof assistantCardPreview;
  assistantDesc: typeof assistantDesc;
  assistantDetailView: typeof assistantDetailView;
  assistantDirty: typeof assistantDirty;
  assistantDraft: typeof assistantDraft;
  assistantFace: typeof assistantFace;
  assistantGlobalDraft: typeof assistantGlobalDraft;
  assistantGlobalView: typeof assistantGlobalView;
  assistantHealth: typeof assistantHealth;
  assistantIcon: typeof assistantIcon;
  assistantIllustration: typeof assistantIllustration;
  assistantInfoTab: typeof assistantInfoTab;
  assistantModelSelect: typeof assistantModelSelect;
  assistantModelTab: typeof assistantModelTab;
  assistantName: typeof assistantName;
  assistantProfiles: typeof assistantProfiles;
  assistantProfilesAvailable: typeof assistantProfilesAvailable;
  assistantPromptOf: typeof assistantPromptOf;
  assistantPromptPreview: typeof assistantPromptPreview;
  assistantPromptTab: typeof assistantPromptTab;
  assistantSaveBar: typeof assistantSaveBar;
  assistantStatsTab: typeof assistantStatsTab;
  baseHost: typeof baseHost;
  bindAdminCreate: typeof bindAdminCreate;
  bindAssistantSettings: typeof bindAssistantSettings;
  bindCharacterEditor: typeof bindCharacterEditor;
  bindHomeSections: typeof bindHomeSections;
  bindModels: typeof bindModels;
  characterCatalog: typeof characterCatalog;
  cmsModal: typeof cmsModal;
  confirmLeaveAssistant: typeof confirmLeaveAssistant;
  connections: typeof connections;
  contentQuery: typeof contentQuery;
  contentRows: typeof contentRows;
  contentSource: typeof contentSource;
  createAdminAccount: typeof createAdminAccount;
  createAdminCharacter: typeof createAdminCharacter;
  createAssistant: typeof createAssistant;
  credentials: typeof credentials;
  currentCharacter: typeof currentCharacter;
  dbCell: typeof dbCell;
  dbColumns: typeof dbColumns;
  dbRows: typeof dbRows;
  dbTables: typeof dbTables;
  deleteBaseCredential: typeof deleteBaseCredential;
  deleteHomeSection: typeof deleteHomeSection;
  deleteModel: typeof deleteModel;
  editingAssistantModel: typeof editingAssistantModel;
  editingModelId: typeof editingModelId;
  editingSectionId: typeof editingSectionId;
  esc: typeof esc;
  fillCharacter: typeof fillCharacter;
  fillModelEditor: typeof fillModelEditor;
  fmtNumber: typeof fmtNumber;
  fmtTime: typeof fmtTime;
  homeSections: typeof homeSections;
  ico: typeof ico;
  initialAvatar: typeof initialAvatar;
  isRedacted: typeof isRedacted;
  loadActionLogs: typeof loadActionLogs;
  loadAssistantDraft: typeof loadAssistantDraft;
  loadAssistantProfiles: typeof loadAssistantProfiles;
  loadChatLogs: typeof loadChatLogs;
  loadDbRows: typeof loadDbRows;
  loadDeferredView: typeof loadDeferredView;
  loadExpressionPreview: typeof loadExpressionPreview;
  loadGlobalDraft: typeof loadGlobalDraft;
  loadHomeSections: typeof loadHomeSections;
  loadLogChatGateways: typeof loadLogChatGateways;
  loadVbeeVoices: typeof loadVbeeVoices;
  logDetailHtml: typeof logDetailHtml;
  logModelName: typeof logModelName;
  logSpeakerCell: typeof logSpeakerCell;
  logText: typeof logText;
  logchatColumns: typeof logchatColumns;
  logchatGateway: typeof logchatGateway;
  logchatOffset: typeof logchatOffset;
  logchatProduct: typeof logchatProduct;
  logchatRequestVersion: typeof logchatRequestVersion;
  logchatRows: typeof logchatRows;
  markAssistantDirty: typeof markAssistantDirty;
  modelFilter: typeof modelFilter;
  modelKeySource: typeof modelKeySource;
  modelLogo: typeof modelLogo;
  modelOptions: typeof modelOptions;
  modelType: typeof modelType;
  modelUsage: typeof modelUsage;
  models: typeof models;
  modelsTab: typeof modelsTab;
  moveHomeSection: typeof moveHomeSection;
  newAssistant: typeof newAssistant;
  normBase: typeof normBase;
  openAssignedModelEditor: typeof openAssignedModelEditor;
  openAssistantCreate: typeof openAssistantCreate;
  openAssistantModelEditor: typeof openAssistantModelEditor;
  openCmsModal: typeof openCmsModal;
  openSectionDialog: typeof openSectionDialog;
  overview: typeof overview;
  patchModel: typeof patchModel;
  profileOf: typeof profileOf;
  profilesNote: typeof profilesNote;
  purposeLabel: typeof purposeLabel;
  purposeModel: typeof purposeModel;
  refreshAssistantPreview: typeof refreshAssistantPreview;
  refreshSectionDialog: typeof refreshSectionDialog;
  reloadModels: typeof reloadModels;
  renderAccess: typeof renderAccess;
  renderActionLogs: typeof renderActionLogs;
  renderAssistantCreate: typeof renderAssistantCreate;
  renderAssistantSettings: typeof renderAssistantSettings;
  renderContent: typeof renderContent;
  renderConversations: typeof renderConversations;
  renderDashboard: typeof renderDashboard;
  renderDatabase: typeof renderDatabase;
  renderHomeSections: typeof renderHomeSections;
  renderModels: typeof renderModels;
  renderSettings: typeof renderSettings;
  renderVoiceLogs: typeof renderVoiceLogs;
  request: typeof request;
  resetCredential: typeof resetCredential;
  saveAccess: typeof saveAccess;
  saveAssistantModelEditor: typeof saveAssistantModelEditor;
  saveAssistantSettings: typeof saveAssistantSettings;
  saveCharacter: typeof saveCharacter;
  saveConnectionKey: typeof saveConnectionKey;
  saveHomeSection: typeof saveHomeSection;
  saveModelAssignments: typeof saveModelAssignments;
  saveModelProfile: typeof saveModelProfile;
  savedHealth: typeof savedHealth;
  sectionAvatar: typeof sectionAvatar;
  sectionListError: typeof sectionListError;
  sectionMatches: typeof sectionMatches;
  selectedModel: typeof selectedModel;
  settings: typeof settings;
  shortTime: typeof shortTime;
  showGenerationNotice: typeof showGenerationNotice;
  toggleCharacterVisibility: typeof toggleCharacterVisibility;
  truthy: typeof truthy;
  updateAccessAccount: typeof updateAccessAccount;
  updateHomeSection: typeof updateHomeSection;
  uploadAdminAvatar: typeof uploadAdminAvatar;
  usable: typeof usable;
  userAssistants: typeof userAssistants;
  vietnamLogTime: typeof vietnamLogTime;
  visibilityButton: typeof visibilityButton;
};
const adminRuntime: AdminRuntime = {
  get ACTION_GROUPS(): typeof ACTION_GROUPS {
    return ACTION_GROUPS;
  },
  get ACTION_STATUS(): typeof ACTION_STATUS {
    return ACTION_STATUS;
  },
  get ASSIGN_TASKS(): typeof ASSIGN_TASKS {
    return ASSIGN_TASKS;
  },
  get ASSISTANT_HUES(): typeof ASSISTANT_HUES {
    return ASSISTANT_HUES;
  },
  get ASSISTANT_ICONS(): typeof ASSISTANT_ICONS {
    return ASSISTANT_ICONS;
  },
  get CREATE_FIELDS(): typeof CREATE_FIELDS {
    return CREATE_FIELDS;
  },
  get EDIT_FIELDS(): typeof EDIT_FIELDS {
    return EDIT_FIELDS;
  },
  get GATEWAY_BASE(): typeof GATEWAY_BASE {
    return GATEWAY_BASE;
  },
  get LOGCHAT_PAGE_SIZE(): typeof LOGCHAT_PAGE_SIZE {
    return LOGCHAT_PAGE_SIZE;
  },
  get PRODUCT_LABELS(): typeof PRODUCT_LABELS {
    return PRODUCT_LABELS;
  },
  get ROLE_LABELS(): typeof ROLE_LABELS {
    return ROLE_LABELS;
  },
  get SECTION_RULES(): typeof SECTION_RULES {
    return SECTION_RULES;
  },
  get SECTION_RULE_HINTS(): typeof SECTION_RULE_HINTS {
    return SECTION_RULE_HINTS;
  },
  get accessControl(): typeof accessControl {
    return accessControl;
  },
  set accessControl(value: typeof accessControl) {
    accessControl = value;
  },
  get actionColumns(): typeof actionColumns {
    return actionColumns;
  },
  set actionColumns(value: typeof actionColumns) {
    actionColumns = value;
  },
  get actionRows(): typeof actionRows {
    return actionRows;
  },
  set actionRows(value: typeof actionRows) {
    actionRows = value;
  },
  get activeAssistantPurpose(): typeof activeAssistantPurpose {
    return activeAssistantPurpose;
  },
  set activeAssistantPurpose(value: typeof activeAssistantPurpose) {
    activeAssistantPurpose = value;
  },
  get activeAssistantTab(): typeof activeAssistantTab {
    return activeAssistantTab;
  },
  set activeAssistantTab(value: typeof activeAssistantTab) {
    activeAssistantTab = value;
  },
  get activeDbTable(): typeof activeDbTable {
    return activeDbTable;
  },
  set activeDbTable(value: typeof activeDbTable) {
    activeDbTable = value;
  },
  get addModel(): typeof addModel {
    return addModel;
  },
  get adminCharacters(): typeof adminCharacters {
    return adminCharacters;
  },
  set adminCharacters(value: typeof adminCharacters) {
    adminCharacters = value;
  },
  get assignmentState(): typeof assignmentState {
    return assignmentState;
  },
  get assignmentValue(): typeof assignmentValue {
    return assignmentValue;
  },
  get assistantCardPreview(): typeof assistantCardPreview {
    return assistantCardPreview;
  },
  get assistantDesc(): typeof assistantDesc {
    return assistantDesc;
  },
  get assistantDetailView(): typeof assistantDetailView {
    return assistantDetailView;
  },
  get assistantDirty(): typeof assistantDirty {
    return assistantDirty;
  },
  set assistantDirty(value: typeof assistantDirty) {
    assistantDirty = value;
  },
  get assistantDraft(): typeof assistantDraft {
    return assistantDraft;
  },
  set assistantDraft(value: typeof assistantDraft) {
    assistantDraft = value;
  },
  get assistantFace(): typeof assistantFace {
    return assistantFace;
  },
  get assistantGlobalDraft(): typeof assistantGlobalDraft {
    return assistantGlobalDraft;
  },
  set assistantGlobalDraft(value: typeof assistantGlobalDraft) {
    assistantGlobalDraft = value;
  },
  get assistantGlobalView(): typeof assistantGlobalView {
    return assistantGlobalView;
  },
  get assistantHealth(): typeof assistantHealth {
    return assistantHealth;
  },
  get assistantIcon(): typeof assistantIcon {
    return assistantIcon;
  },
  get assistantIllustration(): typeof assistantIllustration {
    return assistantIllustration;
  },
  get assistantInfoTab(): typeof assistantInfoTab {
    return assistantInfoTab;
  },
  get assistantModelSelect(): typeof assistantModelSelect {
    return assistantModelSelect;
  },
  get assistantModelTab(): typeof assistantModelTab {
    return assistantModelTab;
  },
  get assistantName(): typeof assistantName {
    return assistantName;
  },
  get assistantProfiles(): typeof assistantProfiles {
    return assistantProfiles;
  },
  set assistantProfiles(value: typeof assistantProfiles) {
    assistantProfiles = value;
  },
  get assistantProfilesAvailable(): typeof assistantProfilesAvailable {
    return assistantProfilesAvailable;
  },
  set assistantProfilesAvailable(value: typeof assistantProfilesAvailable) {
    assistantProfilesAvailable = value;
  },
  get assistantPromptOf(): typeof assistantPromptOf {
    return assistantPromptOf;
  },
  get assistantPromptPreview(): typeof assistantPromptPreview {
    return assistantPromptPreview;
  },
  get assistantPromptTab(): typeof assistantPromptTab {
    return assistantPromptTab;
  },
  get assistantSaveBar(): typeof assistantSaveBar {
    return assistantSaveBar;
  },
  get assistantStatsTab(): typeof assistantStatsTab {
    return assistantStatsTab;
  },
  get baseHost(): typeof baseHost {
    return baseHost;
  },
  get bindAdminCreate(): typeof bindAdminCreate {
    return bindAdminCreate;
  },
  get bindAssistantSettings(): typeof bindAssistantSettings {
    return bindAssistantSettings;
  },
  get bindCharacterEditor(): typeof bindCharacterEditor {
    return bindCharacterEditor;
  },
  get bindHomeSections(): typeof bindHomeSections {
    return bindHomeSections;
  },
  get bindModels(): typeof bindModels {
    return bindModels;
  },
  get characterCatalog(): typeof characterCatalog {
    return characterCatalog;
  },
  set characterCatalog(value: typeof characterCatalog) {
    characterCatalog = value;
  },
  get cmsModal(): typeof cmsModal {
    return cmsModal;
  },
  get confirmLeaveAssistant(): typeof confirmLeaveAssistant {
    return confirmLeaveAssistant;
  },
  get connections(): typeof connections {
    return connections;
  },
  get contentQuery(): typeof contentQuery {
    return contentQuery;
  },
  set contentQuery(value: typeof contentQuery) {
    contentQuery = value;
  },
  get contentRows(): typeof contentRows {
    return contentRows;
  },
  get contentSource(): typeof contentSource {
    return contentSource;
  },
  set contentSource(value: typeof contentSource) {
    contentSource = value;
  },
  get createAdminAccount(): typeof createAdminAccount {
    return createAdminAccount;
  },
  get createAdminCharacter(): typeof createAdminCharacter {
    return createAdminCharacter;
  },
  get createAssistant(): typeof createAssistant {
    return createAssistant;
  },
  get credentials(): typeof credentials {
    return credentials;
  },
  set credentials(value: typeof credentials) {
    credentials = value;
  },
  get currentCharacter(): typeof currentCharacter {
    return currentCharacter;
  },
  get dbCell(): typeof dbCell {
    return dbCell;
  },
  get dbColumns(): typeof dbColumns {
    return dbColumns;
  },
  set dbColumns(value: typeof dbColumns) {
    dbColumns = value;
  },
  get dbRows(): typeof dbRows {
    return dbRows;
  },
  set dbRows(value: typeof dbRows) {
    dbRows = value;
  },
  get dbTables(): typeof dbTables {
    return dbTables;
  },
  set dbTables(value: typeof dbTables) {
    dbTables = value;
  },
  get deleteBaseCredential(): typeof deleteBaseCredential {
    return deleteBaseCredential;
  },
  get deleteHomeSection(): typeof deleteHomeSection {
    return deleteHomeSection;
  },
  get deleteModel(): typeof deleteModel {
    return deleteModel;
  },
  get editingAssistantModel(): typeof editingAssistantModel {
    return editingAssistantModel;
  },
  set editingAssistantModel(value: typeof editingAssistantModel) {
    editingAssistantModel = value;
  },
  get editingModelId(): typeof editingModelId {
    return editingModelId;
  },
  set editingModelId(value: typeof editingModelId) {
    editingModelId = value;
  },
  get editingSectionId(): typeof editingSectionId {
    return editingSectionId;
  },
  set editingSectionId(value: typeof editingSectionId) {
    editingSectionId = value;
  },
  get esc(): typeof esc {
    return esc;
  },
  get fillCharacter(): typeof fillCharacter {
    return fillCharacter;
  },
  get fillModelEditor(): typeof fillModelEditor {
    return fillModelEditor;
  },
  get fmtNumber(): typeof fmtNumber {
    return fmtNumber;
  },
  get fmtTime(): typeof fmtTime {
    return fmtTime;
  },
  get homeSections(): typeof homeSections {
    return homeSections;
  },
  set homeSections(value: typeof homeSections) {
    homeSections = value;
  },
  get ico(): typeof ico {
    return ico;
  },
  get initialAvatar(): typeof initialAvatar {
    return initialAvatar;
  },
  get isRedacted(): typeof isRedacted {
    return isRedacted;
  },
  get loadActionLogs(): typeof loadActionLogs {
    return loadActionLogs;
  },
  get loadAssistantDraft(): typeof loadAssistantDraft {
    return loadAssistantDraft;
  },
  get loadAssistantProfiles(): typeof loadAssistantProfiles {
    return loadAssistantProfiles;
  },
  get loadChatLogs(): typeof loadChatLogs {
    return loadChatLogs;
  },
  get loadDbRows(): typeof loadDbRows {
    return loadDbRows;
  },
  get loadDeferredView(): typeof loadDeferredView {
    return loadDeferredView;
  },
  get loadExpressionPreview(): typeof loadExpressionPreview {
    return loadExpressionPreview;
  },
  get loadGlobalDraft(): typeof loadGlobalDraft {
    return loadGlobalDraft;
  },
  get loadHomeSections(): typeof loadHomeSections {
    return loadHomeSections;
  },
  get loadLogChatGateways(): typeof loadLogChatGateways {
    return loadLogChatGateways;
  },
  get loadVbeeVoices(): typeof loadVbeeVoices {
    return loadVbeeVoices;
  },
  get logDetailHtml(): typeof logDetailHtml {
    return logDetailHtml;
  },
  get logModelName(): typeof logModelName {
    return logModelName;
  },
  get logSpeakerCell(): typeof logSpeakerCell {
    return logSpeakerCell;
  },
  get logText(): typeof logText {
    return logText;
  },
  get logchatColumns(): typeof logchatColumns {
    return logchatColumns;
  },
  set logchatColumns(value: typeof logchatColumns) {
    logchatColumns = value;
  },
  get logchatGateway(): typeof logchatGateway {
    return logchatGateway;
  },
  set logchatGateway(value: typeof logchatGateway) {
    logchatGateway = value;
  },
  get logchatOffset(): typeof logchatOffset {
    return logchatOffset;
  },
  set logchatOffset(value: typeof logchatOffset) {
    logchatOffset = value;
  },
  get logchatProduct(): typeof logchatProduct {
    return logchatProduct;
  },
  set logchatProduct(value: typeof logchatProduct) {
    logchatProduct = value;
  },
  get logchatRequestVersion(): typeof logchatRequestVersion {
    return logchatRequestVersion;
  },
  set logchatRequestVersion(value: typeof logchatRequestVersion) {
    logchatRequestVersion = value;
  },
  get logchatRows(): typeof logchatRows {
    return logchatRows;
  },
  set logchatRows(value: typeof logchatRows) {
    logchatRows = value;
  },
  get markAssistantDirty(): typeof markAssistantDirty {
    return markAssistantDirty;
  },
  get modelFilter(): typeof modelFilter {
    return modelFilter;
  },
  set modelFilter(value: typeof modelFilter) {
    modelFilter = value;
  },
  get modelKeySource(): typeof modelKeySource {
    return modelKeySource;
  },
  get modelLogo(): typeof modelLogo {
    return modelLogo;
  },
  get modelOptions(): typeof modelOptions {
    return modelOptions;
  },
  get modelType(): typeof modelType {
    return modelType;
  },
  get modelUsage(): typeof modelUsage {
    return modelUsage;
  },
  get models(): typeof models {
    return models;
  },
  set models(value: typeof models) {
    models = value;
  },
  get modelsTab(): typeof modelsTab {
    return modelsTab;
  },
  set modelsTab(value: typeof modelsTab) {
    modelsTab = value;
  },
  get moveHomeSection(): typeof moveHomeSection {
    return moveHomeSection;
  },
  get newAssistant(): typeof newAssistant {
    return newAssistant;
  },
  set newAssistant(value: typeof newAssistant) {
    newAssistant = value;
  },
  get normBase(): typeof normBase {
    return normBase;
  },
  get openAssignedModelEditor(): typeof openAssignedModelEditor {
    return openAssignedModelEditor;
  },
  get openAssistantCreate(): typeof openAssistantCreate {
    return openAssistantCreate;
  },
  get openAssistantModelEditor(): typeof openAssistantModelEditor {
    return openAssistantModelEditor;
  },
  get openCmsModal(): typeof openCmsModal {
    return openCmsModal;
  },
  get openSectionDialog(): typeof openSectionDialog {
    return openSectionDialog;
  },
  get overview(): typeof overview {
    return overview;
  },
  set overview(value: typeof overview) {
    overview = value;
  },
  get patchModel(): typeof patchModel {
    return patchModel;
  },
  get profileOf(): typeof profileOf {
    return profileOf;
  },
  get profilesNote(): typeof profilesNote {
    return profilesNote;
  },
  get purposeLabel(): typeof purposeLabel {
    return purposeLabel;
  },
  get purposeModel(): typeof purposeModel {
    return purposeModel;
  },
  get refreshAssistantPreview(): typeof refreshAssistantPreview {
    return refreshAssistantPreview;
  },
  get refreshSectionDialog(): typeof refreshSectionDialog {
    return refreshSectionDialog;
  },
  get reloadModels(): typeof reloadModels {
    return reloadModels;
  },
  get renderAccess(): typeof renderAccess {
    return renderAccess;
  },
  get renderActionLogs(): typeof renderActionLogs {
    return renderActionLogs;
  },
  get renderAssistantCreate(): typeof renderAssistantCreate {
    return renderAssistantCreate;
  },
  get renderAssistantSettings(): typeof renderAssistantSettings {
    return renderAssistantSettings;
  },
  get renderContent(): typeof renderContent {
    return renderContent;
  },
  get renderConversations(): typeof renderConversations {
    return renderConversations;
  },
  get renderDashboard(): typeof renderDashboard {
    return renderDashboard;
  },
  get renderDatabase(): typeof renderDatabase {
    return renderDatabase;
  },
  get renderHomeSections(): typeof renderHomeSections {
    return renderHomeSections;
  },
  get renderModels(): typeof renderModels {
    return renderModels;
  },
  get renderSettings(): typeof renderSettings {
    return renderSettings;
  },
  get renderVoiceLogs(): typeof renderVoiceLogs {
    return renderVoiceLogs;
  },
  get request(): typeof request {
    return request;
  },
  get resetCredential(): typeof resetCredential {
    return resetCredential;
  },
  get saveAccess(): typeof saveAccess {
    return saveAccess;
  },
  get saveAssistantModelEditor(): typeof saveAssistantModelEditor {
    return saveAssistantModelEditor;
  },
  get saveAssistantSettings(): typeof saveAssistantSettings {
    return saveAssistantSettings;
  },
  get saveCharacter(): typeof saveCharacter {
    return saveCharacter;
  },
  get saveConnectionKey(): typeof saveConnectionKey {
    return saveConnectionKey;
  },
  get saveHomeSection(): typeof saveHomeSection {
    return saveHomeSection;
  },
  get saveModelAssignments(): typeof saveModelAssignments {
    return saveModelAssignments;
  },
  get saveModelProfile(): typeof saveModelProfile {
    return saveModelProfile;
  },
  get savedHealth(): typeof savedHealth {
    return savedHealth;
  },
  get sectionAvatar(): typeof sectionAvatar {
    return sectionAvatar;
  },
  get sectionListError(): typeof sectionListError {
    return sectionListError;
  },
  get sectionMatches(): typeof sectionMatches {
    return sectionMatches;
  },
  get selectedModel(): typeof selectedModel {
    return selectedModel;
  },
  get settings(): typeof settings {
    return settings;
  },
  set settings(value: typeof settings) {
    settings = value;
  },
  get shortTime(): typeof shortTime {
    return shortTime;
  },
  get showGenerationNotice(): typeof showGenerationNotice {
    return showGenerationNotice;
  },
  get toggleCharacterVisibility(): typeof toggleCharacterVisibility {
    return toggleCharacterVisibility;
  },
  get truthy(): typeof truthy {
    return truthy;
  },
  get updateAccessAccount(): typeof updateAccessAccount {
    return updateAccessAccount;
  },
  get updateHomeSection(): typeof updateHomeSection {
    return updateHomeSection;
  },
  get uploadAdminAvatar(): typeof uploadAdminAvatar {
    return uploadAdminAvatar;
  },
  get usable(): typeof usable {
    return usable;
  },
  get userAssistants(): typeof userAssistants {
    return userAssistants;
  },
  get vietnamLogTime(): typeof vietnamLogTime {
    return vietnamLogTime;
  },
  get visibilityButton(): typeof visibilityButton {
    return visibilityButton;
  },
};
// Controllers are created once; DOM events still bind at their original call sites.
const controllers = {
  ...createPresentationController(adminRuntime),
  ...createDashboardController(adminRuntime),
  ...createCharactersController(adminRuntime),
  ...createHomeSectionsController(adminRuntime),
  ...createAssignmentsController(adminRuntime),
  ...createModelsController(adminRuntime),
  ...createAssistantsController(adminRuntime),
  ...createLogsController(adminRuntime),
  ...createDatabaseController(adminRuntime),
  ...createAccessController(adminRuntime),
  ...createBootstrapController(adminRuntime),
};

document.documentElement.dataset.app = "admin";
const root = document.querySelector<HTMLDivElement>("#admin-root")!;
root.innerHTML = `<div class="adminShell"><aside class="adminSide"><div class="adminBrand"><span class="logo">CMS</span><span>Avibi CMS<small>Quản trị nền tảng</small></span></div><nav class="adminNav"><div class="adminNavGroup"><span>Tổng quan</span><button class="active" data-view="dashboard"><i class="fi-rr-apps vi" aria-hidden="true"></i>Tổng quan</button></div><div class="adminNavGroup"><span>Nội dung</span><button class="" data-view="content"><i class="fi-rr-users-alt vi" aria-hidden="true"></i>Nhân vật</button><button data-view="action-sounds"><i class="fi-rr-volume vi" aria-hidden="true"></i>Âm hành động</button><button data-view="background-music"><i class="fi-rr-music-alt vi" aria-hidden="true"></i>Nhạc nền</button><button class="" data-view="home-sections"><i class="fi-rr-apps-sort vi" aria-hidden="true"></i>Danh mục trang chủ</button><button class="" data-view="assistant-config"><i class="fi-rr-sparkles vi" aria-hidden="true"></i>Trợ lý AI</button></div><div class="adminNavGroup"><span>AI & model</span><button class="" data-view="models"><i class="fi-rr-settings-sliders vi" aria-hidden="true"></i>Cấu hình AI</button><button class="" data-view="settings"><i class="fi-rr-shuffle vi" aria-hidden="true"></i>Phân công model</button></div><div class="adminNavGroup"><span>Giám sát</span><button class="" data-view="conversations"><i class="fi-rr-comment-alt vi" aria-hidden="true"></i>Logchat</button><button data-view="voice-logs"><i class="fi-rr-volume vi" aria-hidden="true"></i>Log voice</button><button class="" data-view="action-logs"><i class="fi-rr-time-past vi" aria-hidden="true"></i>Nhật ký hoạt động</button></div><div class="adminNavGroup"><span>Hệ thống</span><button class="" data-view="access"><i class="fi-rr-shield-check vi" aria-hidden="true"></i>Truy cập</button><button class="" data-view="database"><i class="fi-rr-database vi" aria-hidden="true"></i>Database</button></div></nav><div class="adminMeta mono faint">Khu vực quản trị riêng · tài khoản admin</div></aside><main class="adminMain"><div class="top"><div><h1 id="page-title">Tổng quan sản phẩm</h1><p id="page-subtitle">Sức khỏe hệ thống và nội dung sản phẩm</p></div><div class="topActions"><a class="btn" href="/role-play-ai" style="text-decoration:none"><i class="fi-rr-arrow-up-right-from-square vi" aria-hidden="true"></i>Mở Chat Bot AI</a><button class="btn" id="refresh"><i class="fi-rr-refresh vi" aria-hidden="true"></i>Làm mới</button></div></div><section class="view active" id="dashboard"></section><section class="view" id="content"></section><section class="view" id="action-sounds"></section><section class="view" id="background-music"></section><section class="view" id="home-sections"></section><section class="view" id="assistant-config"></section><section class="view" id="models"></section><section class="view" id="settings"></section><section class="view" id="conversations"></section><section class="view" id="voice-logs"></section><section class="view" id="action-logs"></section><section class="view" id="access"></section><section class="view" id="database"></section></main></div>`;
let overview: Overview | null = null;
let settings: Settings | null = null;
let accessControl: AccessControl | null = null;
let characterCatalog: CharacterCatalog = {
  preset_catalog: [],
  user_characters: [],
};
let credentials: CredentialState | null = null;
let adminCharacters: AdminCharacter[] = [];
let models: ModelConfig[] = [];
let dbTables: DbTable[] = [];
let activeDbTable = "users";
const esc = (value: unknown) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (char) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        char
      ]!,
  );
const vietnamLogTime = new Intl.DateTimeFormat("vi-VN", {
  timeZone: "Asia/Ho_Chi_Minh",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hourCycle: "h23",
});
function formatVietnamLogTime(value: unknown): string {
  return controllers.formatVietnamLogTime(value);
}
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!response.ok) {
    const body = await response.text();
    try {
      const detail = JSON.parse(body).detail;
      if (
        detail &&
        typeof detail === "object" &&
        String(detail.code || "").startsWith("character_policy_")
      )
        throw new Error(
          String(detail.message || "Không thể kiểm duyệt nhân vật."),
        );
    } catch (error) {
      if (error instanceof Error && error.name !== "SyntaxError") throw error;
    }
    throw new Error(
      response.status === 401
        ? "Bạn chưa đăng nhập CMS hoặc phiên đăng nhập đã hết."
        : body,
    );
  }
  return response.json();
}
function showGenerationNotice(
  plan: NonNullable<ModelUpdate["expression_generation"]>,
): void {
  return controllers.showGenerationNotice(plan);
}
const ROLE_LABELS: Record<string, string> = {
  companion: "Đồng hành",
  study: "Học tập",
  work: "Công việc",
  entertainment: "Giải trí",
  romance: "Tình cảm",
  roleplay: "Role play",
};
const fmtNumber = (value: number | undefined) =>
  (value ?? 0).toLocaleString("vi-VN");
const fmtTime = (value: string) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleTimeString("vi-VN", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
};
const initialAvatar = (name: string, size = 26) =>
  `<span class="ovAvatar" style="width:${size}px;height:${size}px;font-size:${Math.round(size * 0.42)}px">${esc((name || "?").trim()[0]?.toUpperCase() || "?")}</span>`;
function renderDashboard(): void {
  return controllers.renderDashboard();
}
const CREATE_FIELDS = `<label class="field">Tên nhân vật<input id="new-character-name" placeholder="Ví dụ: Linh"/></label><label class="field">Vai trò<input id="new-character-role" value="companion" placeholder="companion, study, work..."/></label><label class="field">Nhóm<select id="new-character-category"><option value="utility">Hữu ích</option><option value="entertainment">Giải trí</option></select></label><label class="field">Ảnh nhân vật<input type="file" id="new-character-avatar" accept="image/png,image/jpeg,image/webp,image/gif"/><span class="hint">JPG, PNG, WEBP hoặc GIF · tối đa 5 MB</span></label><label class="field full">Mô tả<textarea id="new-character-description"></textarea></label><label class="field full">System prompt<textarea class="largePrompt" id="new-character-prompt"></textarea></label><label class="field full">Lời chào đầu tiên<textarea id="new-character-greeting"></textarea></label>`;
const EDIT_FIELDS = `<label class="field full">Chọn nhân vật<select id="character-select"></select></label><label class="field full" id="home-section-field">Vị trí trên trang chủ<select id="character-home-section"><option value="auto">Hiện trong Nhân vật hệ thống</option><option value="hidden">Ẩn khỏi trang chủ</option></select><span class="hint">Chỉ áp dụng cho nhân vật hệ thống do admin quản lý.</span></label><label class="field">Tên<input id="character-name"/></label><label class="field">Vai trò<input id="character-role"/></label><label class="field full">Mô tả<textarea id="character-description"></textarea></label><label class="field full">System prompt riêng<textarea class="largePrompt" id="character-system-prompt"></textarea></label><label class="field full">Scenario<textarea id="character-scenario"></textarea></label><label class="field full">Lời chào đầu tiên<textarea id="character-greeting"></textarea></label><label class="field full">Thay Ảnh nhân vật<input type="file" id="character-avatar-file" accept="image/png,image/jpeg,image/webp,image/gif"/><span class="hint">Để trống nếu muốn giữ ảnh hiện tại.</span></label><label class="field">Goals, mỗi dòng một mục<textarea id="character-goals"></textarea></label><label class="field">Behavior rules, mỗi dòng một mục<textarea id="character-rules"></textarea></label>`;
let contentSource: "preset" | "user" = "preset";
let contentQuery = "";
const ico = (name: string) =>
  `<i class="fi-rr-${name} vi" aria-hidden="true"></i>`;
function cmsModal(
  id: string,
  title: string,
  eyebrow: string,
  body: string,
  footer: string,
  wide = true,
): string {
  return controllers.cmsModal(id, title, eyebrow, body, footer, wide);
}
function openCmsModal(id: string): void {
  return controllers.openCmsModal(id);
}
function closeCmsModal(el: Element | null): void {
  return controllers.closeCmsModal(el);
}
document.addEventListener("click", (event) => {
  const target = event.target as HTMLElement;
  const opener = target.closest<HTMLElement>("[data-open]");
  if (opener) return openCmsModal(opener.dataset.open!);
  if (target.closest("[data-close]"))
    return closeCmsModal(target.closest(".scrim"));
  if (target.classList.contains("scrim")) closeCmsModal(target);
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape")
    document
      .querySelectorAll<HTMLElement>(".scrim:not([hidden])")
      .forEach((el) => (el.hidden = true));
});
/** Nút ẩn/hiện nhân vật hệ thống trên trang chủ (đổi home_section giữa "hidden" và "auto"). */
const visibilityButton = (x: AdminCharacter) =>
  x.home_section === "hidden"
    ? `<button class="btn sm" data-toggle-visibility="${esc(x.id)}" title="Hiện ${esc(x.spec.name)} trên trang chủ">${ico("eye")}Hiện</button>`
    : `<button class="btn sm" data-toggle-visibility="${esc(x.id)}" title="Ẩn ${esc(x.spec.name)} khỏi trang chủ">${ico("eye-crossed")}Ẩn</button>`;
async function toggleCharacterVisibility(
  button: HTMLButtonElement,
): Promise<void> {
  return controllers.toggleCharacterVisibility(button);
}
function contentRows(): string {
  return controllers.contentRows();
}
async function loadVbeeVoices(): Promise<void> {
  return controllers.loadVbeeVoices();
}
function renderContent(): void {
  return controllers.renderContent();
}
function currentCharacter(): AdminCharacter | undefined {
  return controllers.currentCharacter();
}
function fillCharacter(): void {
  return controllers.fillCharacter();
}
async function loadExpressionPreview(
  item: AdminCharacter,
  attempt = 0,
): Promise<void> {
  return controllers.loadExpressionPreview(item, attempt);
}
function bindCharacterEditor(): void {
  return controllers.bindCharacterEditor();
}
async function saveCharacter(): Promise<void> {
  return controllers.saveCharacter();
}

let homeSections: CmsHomeSection[] = [];
let editingSectionId = "";
const SECTION_RULES: Record<string, string> = {
  popular: "Phổ biến nhất",
  trending: "Đang thịnh hành",
  top_rated: "Đánh giá cao",
  favorites: "Được yêu thích",
  featured: "Nổi bật",
  tags: "Theo tag",
};
const SECTION_RULE_HINTS: Record<string, string> = {
  popular: "Sắp xếp theo lượt dùng",
  trending: "Sắp xếp theo điểm trending",
  top_rated: "Sắp xếp theo điểm đánh giá",
  favorites: "Sắp xếp theo tổng lượt cảm xúc",
  featured: "Nhân vật được ghim nổi bật",
  tags: "Lấy nhân vật có tag hoặc vai trò khớp",
};
async function loadHomeSections(): Promise<void> {
  return controllers.loadHomeSections();
}
/** Nhân vật hệ thống khớp một danh mục: luật theo tag lọc theo tag/vai trò, các luật xếp hạng lấy toàn bộ. */
function sectionMatches(rule: string, tags: string[]): AdminCharacter[] {
  return controllers.sectionMatches(rule, tags);
}
const sectionAvatar = (c: AdminCharacter, size = 24) =>
  c.spec.avatar_url
    ? `<img class="ovAvatar" src="${esc(c.spec.avatar_url)}" alt="" style="width:${size}px;height:${size}px">`
    : `<span class="ovAvatar" style="width:${size}px;height:${size}px;font-size:${Math.round(size * 0.42)}px">${esc((c.spec.name || "?")[0].toUpperCase())}</span>`;
function renderHomeSections(): void {
  return controllers.renderHomeSections();
}
function refreshSectionDialog(): void {
  return controllers.refreshSectionDialog();
}
function openSectionDialog(section?: CmsHomeSection): void {
  return controllers.openSectionDialog(section);
}
function bindHomeSections(): void {
  return controllers.bindHomeSections();
}
function sectionListError(error: unknown): void {
  return controllers.sectionListError(error);
}
async function saveHomeSection(): Promise<undefined> {
  return controllers.saveHomeSection();
}
async function updateHomeSection(
  id: string,
  changes: Partial<CmsHomeSection>,
): Promise<void> {
  return controllers.updateHomeSection(id, changes);
}
async function moveHomeSection(id: string, dir: number): Promise<void> {
  return controllers.moveHomeSection(id, dir);
}
async function deleteHomeSection(id: string): Promise<void> {
  return controllers.deleteHomeSection(id);
}
function bindAdminCreate(): void {
  return controllers.bindAdminCreate();
}
async function uploadAdminAvatar(
  path: string,
  file: File,
): Promise<{
  avatar_url: string;
  expression_status?: string | undefined;
  images_queued?: number | undefined;
}> {
  return controllers.uploadAdminAvatar(path, file);
}
async function createAdminCharacter(): Promise<void> {
  return controllers.createAdminCharacter();
}
function modelOptions(selected = "", includeEmpty = false): string {
  return controllers.modelOptions(selected, includeEmpty);
}
const modelPurposeLabels: Record<string, string> = {
  response: "Trả lời hội thoại",
  suggestion: "Gợi ý trả lời",
  suggestion_fallback: "Dự phòng gợi ý",
  compiler: "Tạo nhân vật",
  moderation: "Kiểm duyệt",
  fallback: "Dự phòng",
  avatar_image: "Tạo avatar biểu cảm",
  emotion: "Nhận diện cảm xúc",
  emotion_fallback: "Dự phòng cảm xúc",
  tts: "Phát giọng nói Role Play",
  assistant_general: "Assistant · Tổng quát",
  assistant_general_fallback: "Dự phòng · Tổng quát",
  assistant_psychology_fallback: "Dự phòng · Tâm lý",
  assistant_health_fallback: "Dự phòng · Sức khỏe",
  assistant_homework_fallback: "Dự phòng · Bài tập",
  assistant_tarot_fallback: "Dự phòng · Tarot",
  assistant_psychology: "Assistant · Tâm lý",
  assistant_health: "Assistant · Sức khỏe",
  assistant_homework: "Assistant · Bài tập",
  assistant_tarot: "Assistant · Tarot",
  assistant_tuvi: "Assistant · Tử vi",
  assistant_tuvi_fallback: "Dự phòng · Tử vi",
  assistant_suggestion: "Assistant · Gợi ý trả lời",
};
/* ---------- Cấu hình AI (theo màn admAI của prototype) ---------- */
const GATEWAY_BASE = "https://gateway.avibi.ai/v1";
let modelsTab: "models" | "conns" = "models";
let modelFilter = { q: "", provider: "all", type: "all", status: "all" };
let editingModelId = "";
const normBase = (base: string) => base.replace(/\/+$/, "").toLowerCase();
const baseHost = (base: string) => {
  try {
    return new URL(base).host;
  } catch {
    return base || "—";
  }
};
const modelType = (m: ModelConfig) =>
  m.purposes.includes("tts")
    ? "TTS"
    : m.purposes.includes("avatar_image")
      ? "Ảnh"
      : "Chat";
/** Nhãn tác vụ; tác vụ dự phòng chưa có nhãn riêng thì ghép từ nhãn tác vụ gốc. */
const purposeLabel = (p: string) => {
  if (modelPurposeLabels[p]) return modelPurposeLabels[p];
  const match = p.match(/^(.*)_fallback(?:_(\d))?$/);
  if (match && modelPurposeLabels[match[1]])
    return `${modelPurposeLabels[match[1]].replace(/^Assistant · /, "")} · dự phòng ${match[2] || 1}`;
  return p;
};
const modelUsage = (m: ModelConfig) => m.purposes.map(purposeLabel);
/** Nguồn API key mà model đang dùng: key riêng, key theo API base hoặc key gateway chung. */
function modelKeySource(m: ModelConfig): {
  ok: boolean;
  label: string;
  hint: string;
} {
  return controllers.modelKeySource(m);
}

function connections(): Connection[] {
  return controllers.connections();
}
const modelLogo = (m: ModelConfig, size = 30) => {
  let hash = 0;
  for (const ch of m.provider + m.name)
    hash = (hash * 31 + ch.charCodeAt(0)) % 360;
  return `<span class="mdlLogo" style="width:${size}px;height:${size}px;background:hsl(${hash} 45% 45%)">${esc((m.logo || m.name || "?").slice(0, 2).toUpperCase())}</span>`;
};
function renderModels(): void {
  return controllers.renderModels();
}
function bindModels(): void {
  return controllers.bindModels();
}
/** Lưu key cho một kết nối: gateway AVIBI dùng key chung, API base khác dùng key theo API base. */
async function saveConnectionKey(): Promise<void> {
  return controllers.saveConnectionKey();
}
function selectedModel(): ModelConfig | undefined {
  return controllers.selectedModel();
}
function fillModelEditor(): void {
  return controllers.fillModelEditor();
}
async function saveModelProfile(): Promise<void> {
  return controllers.saveModelProfile();
}
async function resetCredential(): Promise<void> {
  return controllers.resetCredential();
}
async function deleteBaseCredential(id: string): Promise<void> {
  return controllers.deleteBaseCredential(id);
}
async function reloadModels(): Promise<void> {
  return controllers.reloadModels();
}
async function addModel(): Promise<void> {
  return controllers.addModel();
}
async function patchModel(
  id: string,
  body: Record<string, unknown>,
): Promise<void> {
  return controllers.patchModel(id, body);
}
async function deleteModel(id: string): Promise<void> {
  return controllers.deleteModel(id);
}
function assignmentValue(purpose: string): string {
  return controllers.assignmentValue(purpose);
}
const assistantPurposes = [
  "assistant_general",
  "assistant_psychology",
  "assistant_health",
  "assistant_homework",
  "assistant_tarot",
  "assistant_tuvi",
  "assistant_suggestion",
];
/* ---------- Trợ lý AI (theo màn "as-cms" của prototype) ---------- */

const ASSISTANT_INFO: Record<
  string,
  {
    name: string;
    desc: string;
  }
> = {
  assistant_general: {
    name: "Trợ lý AI chung",
    desc: "Hỏi mình bất cứ điều gì",
  },
  assistant_psychology: {
    name: "Tâm lý",
    desc: "Lắng nghe và cùng bạn gỡ rối cảm xúc",
  },
  assistant_health: {
    name: "Sức khỏe",
    desc: "Thông tin sức khỏe thận trọng, dễ hiểu",
  },
  assistant_homework: {
    name: "Học tập",
    desc: "Giải thích từng bước từ tài liệu của bạn",
  },
  assistant_tarot: {
    name: "Tarot",
    desc: "Gửi Bát Tự, lá số hoặc trải bài minh họa",
  },
  assistant_tuvi: {name:"Tử vi & Bát Tự",desc:"Diễn giải lá số và thông tin ngày sinh"},
  assistant_suggestion: {
    name: "Gợi ý trả lời",
    desc: "Tác vụ nền: sinh 3 gợi ý dưới mỗi câu trả lời",
  },
};
const ASSISTANT_ICONS: [string, string][] = [
  ["sparkles", "Đa năng"],
  ["book-alt", "Học tập"],
  ["heart", "Sức khỏe"],
  ["cloud", "Cảm xúc"],
  ["moon-stars", "Chiêm nghiệm"],
  ["users", "Giao tiếp"],
  ["globe", "Ngoại ngữ"],
  ["document", "Tài liệu"],
];
const ASSISTANT_HUES = [172, 205, 140, 32, 275, 350, 220, 48];
let assistantProfiles: AssistantProfiles = { order: [], items: {} };
let assistantProfilesAvailable = true;
let activeAssistantPurpose = "global";
let activeAssistantTab: AssistantTab = "info";
let assistantDraft: AssistantDraft | null = null;
let assistantGlobalDraft: GlobalDraft | null = null;
let assistantDirty = false;
const defaultProfile = (purpose: string): AssistantProfile => ({
  title: ASSISTANT_INFO[purpose]?.name || purpose,
  slogan: "",
  description: ASSISTANT_INFO[purpose]?.desc || "",
  greeting: "",
  starters: [],
  visible: true,
  user_pick: false,
});
const profileOf = (purpose: string) =>
  assistantProfiles.items[purpose] || defaultProfile(purpose);
/** Trợ lý hiển thị cho người dùng: 5 trợ lý có sẵn và các trợ lý admin tạo thêm. */
const userAssistants = () => [
  ...assistantPurposes.filter((p) => p !== "assistant_suggestion"),
  ...assistantProfiles.order.filter((p) => !assistantPurposes.includes(p)),
];
async function loadAssistantProfiles(): Promise<void> {
  return controllers.loadAssistantProfiles();
}
const purposeModel = (role: string) =>
  models.find((x) => x.purposes.includes(role));
const assistantPromptOf = (model: ModelConfig | undefined, field: string) =>
  model
    ? String((model as unknown as Record<string, unknown>)[field] || "")
    : "";
function loadAssistantDraft(purpose: string): AssistantDraft {
  return controllers.loadAssistantDraft(purpose);
}
function loadGlobalDraft(): GlobalDraft {
  return controllers.loadGlobalDraft();
}
/** Tình trạng chuỗi model của một tác vụ: đủ 3 model, thiếu dự phòng hoặc có model đang ẩn. */
function assistantHealth(ids: string[]): { k: string; t: string; n: number } {
  return controllers.assistantHealth(ids);
}
const savedHealth = (purpose: string) =>
  assistantHealth(
    [purpose, purpose + "_fallback", purpose + "_fallback_2"].map(
      (role) => purposeModel(role)?.id || "",
    ),
  );
const assistantName = (purpose: string) =>
  purpose === "assistant_suggestion"
    ? ASSISTANT_INFO[purpose].name
    : purpose === "assistant_general"
      ? ASSISTANT_INFO[purpose].name
      : profileOf(purpose).title;
const assistantDesc = (purpose: string) =>
  purpose === "assistant_suggestion"
    ? ASSISTANT_INFO[purpose].desc
    : profileOf(purpose).description;
function assistantFace(purpose: string, size = 34): string {
  return controllers.assistantFace(purpose, size);
}
function assistantIllustration(purpose: string): string {
  return controllers.assistantIllustration(purpose);
}
const assistantIcon = (purpose: string, large = false) =>
  purpose === "assistant_suggestion" || purpose === "global"
    ? `<span class="tl-ic${large ? " lg" : ""}">${ico(purpose === "global" ? "settings-sliders" : "sparkles")}</span>`
    : assistantFace(purpose, large ? 44 : 34);
/** Thẻ trợ lý như trên trang chủ Trợ lý AI, dùng cho phần xem trước. */
function assistantCardPreview(o: {
  face: string;
  illustration: string;
  title: string;
  description: string;
  requests: number;
  hidden?: boolean;
}): string {
  return controllers.assistantCardPreview(o);
}
const profilesNote = () =>
  assistantProfilesAvailable
    ? ""
    : `<div class="note">Backend chưa có API <span class="mono">/v1/admin/assistant-profiles</span> nên phần hiển thị và thống kê chỉ để xem, không lưu được.</div>`;
function assistantSaveBar(): string {
  return controllers.assistantSaveBar();
}
function assistantModelSelect(
  id: string,
  selected: string,
  placeholder = "— Chưa chọn —",
): string {
  return controllers.assistantModelSelect(id, selected, placeholder);
}
function assistantGlobalView(): string {
  return controllers.assistantGlobalView();
}
function assistantInfoTab(purpose: string): string {
  return controllers.assistantInfoTab(purpose);
}
function assistantModelTab(purpose: string): string {
  return controllers.assistantModelTab(purpose);
}
function assistantPromptPreview(purpose: string, prompt: string): string {
  return controllers.assistantPromptPreview(purpose, prompt);
}
function assistantPromptTab(purpose: string): string {
  return controllers.assistantPromptTab(purpose);
}
function assistantStatsTab(purpose: string): string {
  return controllers.assistantStatsTab(purpose);
}
function assistantDetailView(purpose: string): string {
  return controllers.assistantDetailView(purpose);
}
function renderAssistantSettings(): void {
  return controllers.renderAssistantSettings();
}
function markAssistantDirty(): void {
  return controllers.markAssistantDirty();
}
function confirmLeaveAssistant(): boolean {
  return controllers.confirmLeaveAssistant();
}
function refreshAssistantPreview(): void {
  return controllers.refreshAssistantPreview();
}
function bindAssistantSettings(): void {
  return controllers.bindAssistantSettings();
}
let editingAssistantModel = "";
function openAssistantModelEditor(id: string): void {
  return controllers.openAssistantModelEditor(id);
}
async function saveAssistantModelEditor(): Promise<void> {
  return controllers.saveAssistantModelEditor();
}
async function saveAssistantSettings(): Promise<void> {
  return controllers.saveAssistantSettings();
}
/* Hộp thoại tạo trợ lý AI */

let newAssistant: NewAssistantForm = {
  title: "",
  slogan: "",
  description: "",
  greeting: "",
  icon: "sparkles",
  hue: 172,
  hair: 0,
  main: "",
  f1: "",
  prompt: "",
  visible: true,
};
function renderAssistantCreate(): void {
  return controllers.renderAssistantCreate();
}
function openAssistantCreate(): void {
  return controllers.openAssistantCreate();
}
async function createAssistant(): Promise<undefined> {
  return controllers.createAssistant();
}
/* ---------- Phân công model (theo admAssign của prototype) ---------- */
const ASSIGN_TASKS: [string, string, string][] = [
  ["response", "Trả lời", "Model chính trả lời người dùng trong Chat Bot AI"],
  ["suggestion", "Gợi ý", "Tạo các lựa chọn trả lời nhanh"],
  [
    "suggestion_fallback",
    "Gợi ý · dự phòng 1",
    "Dùng khi model gợi ý chính lỗi",
  ],
  [
    "suggestion_fallback_2",
    "Gợi ý · dự phòng 2",
    "Dùng khi hai model gợi ý trước đều lỗi",
  ],
  ["compiler", "Tạo nhân vật", "Tóm tắt mô tả và biên dịch CharacterSpec"],
  ["moderation", "Kiểm duyệt", "Phân tích an toàn nội dung và ngữ cảnh"],
  [
    "fallback",
    "Dự phòng hội thoại · lớp 1",
    "Trả lời khi model chính không khả dụng",
  ],
  [
    "fallback_2",
    "Dự phòng hội thoại · lớp 2",
    "Trả lời khi model chính và lớp 1 đều lỗi",
  ],
  [
    "avatar_image",
    "Tạo avatar biểu cảm",
    "Chỉnh ảnh nguồn thành chân dung và sinh bộ nét mặt",
  ],
  ["emotion", "Nhận diện cảm xúc", "Phân loại cảm xúc của câu trả lời"],
  [
    "emotion_fallback",
    "Nhận diện cảm xúc · dự phòng 1",
    "Dùng khi model cảm xúc chính lỗi",
  ],
  [
    "emotion_fallback_2",
    "Nhận diện cảm xúc · dự phòng 2",
    "Dùng khi hai model cảm xúc trước đều lỗi",
  ],
  ["tts", "Phát giọng nói TTS", "Gọi /audio/speech khi người dùng bấm Nghe"],
];
function assignmentState(modelId: string): string[] {
  return controllers.assignmentState(modelId);
}
function renderSettings(): void {
  return controllers.renderSettings();
}
function openAssignedModelEditor(id: string): void {
  return controllers.openAssignedModelEditor(id);
}
async function saveModelAssignments(): Promise<void> {
  return controllers.saveModelAssignments();
}
/* ---------- Logchat và Nhật ký hoạt động (theo admLog / admActivity của prototype) ---------- */

let logchatProduct = "all";
let logchatGateway = "";
const LOGCHAT_PAGE_SIZE = 100;
let logchatOffset = 0;
let logchatRequestVersion = 0;
let logchatRows: LogRow[] = [];
let actionRows: LogRow[] = [];
const logText = (value: unknown) =>
  value === null || value === undefined ? "" : String(value);
const shortTime = (value: unknown, withSeconds = true) => {
  const date = new Date(logText(value));
  if (Number.isNaN(date.getTime())) return logText(value) || "—";
  const today = new Date().toDateString() === date.toDateString();
  const time = date.toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    ...(withSeconds ? { second: "2-digit" } : {}),
  });
  return today
    ? time
    : `${date.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" })} ${time}`;
};
const truthy = (value: unknown) =>
  ["true", "có", "yes", "1"].includes(logText(value).trim().toLowerCase());
const usable = (value: unknown) => {
  const v = logText(value).trim();
  return v && !/^(không phân công|chưa ghi nhận|—|-)$/i.test(v) ? v : "";
};
function logModelName(
  value: unknown,
  configId: unknown,
  product: unknown,
): string {
  return controllers.logModelName(value, configId, product);
}
const PRODUCT_LABELS: Record<string, string> = {
  roleplay: "Chat Bot AI",
  assistant: "Trợ lý AI",
};
/** Hộp thoại xem toàn bộ trường của một dòng log. */
function logSpeakerCell(row: LogRow): string {
  return controllers.logSpeakerCell(row);
}
function logDetailHtml(row: LogRow, columns: string[]): string {
  return controllers.logDetailHtml(row, columns);
}
let logchatColumns: string[] = [];
let actionColumns: string[] = [];
async function loadLogChatGateways(): Promise<void> {
  return controllers.loadLogChatGateways();
}
async function renderConversations(): Promise<void> {
  return controllers.renderConversations();
}
async function loadChatLogs(): Promise<void> {
  return controllers.loadChatLogs();
}
const ACTION_GROUPS: [string, string][] = [
  ["all", "Tất cả"],
  ["auth", "Đăng nhập"],
  ["navigation", "Mở app"],
  ["assistant", "Trợ lý AI"],
  ["roleplay", "Chat Bot AI"],
  ["document", "Tài liệu"],
  ["api", "API khác"],
];
const ACTION_STATUS: Record<string, [string, string]> = {
  success: ["ok", "Thành công"],
  partial: ["warn", "Câu trả lời dở"],
  error: ["bad", "Lỗi"],
};
function renderActionLogs(): void {
  return controllers.renderActionLogs();
}
async function loadActionLogs(): Promise<void> {
  return controllers.loadActionLogs();
}
/* ---------- Database Explorer (theo admDB của prototype) ---------- */
let dbRows: Record<string, unknown>[] = [];
let dbColumns: string[] = [];
const dbCell = (value: unknown) =>
  value === null || value === undefined
    ? ""
    : typeof value === "object"
      ? JSON.stringify(value)
      : String(value);
const isRedacted = (value: string) =>
  /^\[?(redacted|đã che)\]?$/i.test(value.trim()) ||
  /^\*{3,}$/.test(value.trim());

const { renderVoiceLogs } = createCmsLogViews(
  request,
  esc,
  formatVietnamLogTime,
);
function renderDatabase(): void {
  return controllers.renderDatabase();
}
async function loadDbRows(): Promise<void> {
  return controllers.loadDbRows();
}
function renderAccess(): void {
  return controllers.renderAccess();
}
async function saveAccess(): Promise<void> {
  return controllers.saveAccess();
}
async function createAdminAccount(): Promise<void> {
  return controllers.createAdminAccount();
}
async function updateAccessAccount(
  userId: string,
  changes: Record<string, unknown>,
): Promise<void> {
  return controllers.updateAccessAccount(userId, changes);
}
async function load(): Promise<void> {
  return controllers.load();
}
// Hidden panels must not fetch logs, table rows or character media on startup.
async function loadDeferredView(view?: string): Promise<void> {
  return controllers.loadDeferredView(view);
}
void fetch("/v1/worlds/config").then(r=>r.json()).then(c=>{if(c.enabled){const nav=document.querySelector(".adminNav");if(nav){const link=document.createElement("a");link.href="/worlds/admin";link.className="btn";link.textContent="✧ Worlds · CMS";nav.appendChild(link);}}}).catch(()=>{});
document.querySelectorAll<HTMLButtonElement>("[data-view]").forEach((button) =>
  button.addEventListener("click", () => {
    document
      .querySelectorAll("[data-view]")
      .forEach((x) => x.classList.remove("active"));
    if (button.dataset.view !== "action-sounds")
      document
        .querySelectorAll<HTMLAudioElement>("#action-sounds audio")
        .forEach((audio) => audio.pause());
    if (button.dataset.view !== "background-music")
      document
        .querySelectorAll<HTMLAudioElement>("#background-music audio")
        .forEach((audio) => audio.pause());
    button.classList.add("active");
    document
      .querySelectorAll(".view")
      .forEach((x) => x.classList.remove("active"));
    document.querySelector(`#${button.dataset.view}`)!.classList.add("active");
    const labels: Record<string, [string, string]> = {
      access: [
        "Quản lý truy cập",
        "Chế độ bảo trì, tài khoản quản trị và trạng thái người dùng",
      ],
      dashboard: [
        "Tổng quan sản phẩm",
        "Sức khỏe hệ thống và nội dung sản phẩm",
      ],
      content: [
        "Nhân vật",
        "Danh sách nhân vật hệ thống và nhân vật do người dùng tạo",
      ],
      "action-sounds": [
        "Âm hành động",
        "Thư viện sound, từ khóa nhận diện và âm lượng",
      ],
      "background-music": [
        "Nhạc nền Role Play",
        "Âm lượng, danh sách bài và nhạc phát tại trang chủ",
      ],
      "home-sections": [
        "Danh mục trang chủ",
        "Các nhóm nhân vật hiển thị trên trang chủ Chat Bot AI",
      ],
      conversations: [
        "Logchat",
        "Log hỏi đáp theo sản phẩm · bấm một dòng để xem đầy đủ",
      ],
      "voice-logs": ["Log voice", "Theo dõi tạo audio, lượt Nghe và latency"],
      "action-logs": [
        "Nhật ký hoạt động",
        "Không ghi mật khẩu, token hay nội dung request",
      ],
      models: [
        "Cấu hình AI",
        "Model và kết nối dùng chung cho Chat Bot AI và Trợ lý AI",
      ],
      "assistant-config": [
        "Trợ lý AI",
        "Chọn một trợ lý bên trái để chỉnh hiển thị, model, prompt và xem thống kê",
      ],
      database: ["Database Explorer", "Chỉ đọc · dữ liệu nhạy cảm được che"],
      settings: ["Phân công model", "Gán model cho từng tác vụ của hệ thống"],
    };
    void loadDeferredView(button.dataset.view);
    if (button.dataset.view === "action-sounds") void renderActionSounds();
    if (button.dataset.view === "background-music")
      void renderBackgroundMusic();
    const label = labels[button.dataset.view!];
    document.querySelector("#page-title")!.textContent = label[0];
    document.querySelector("#page-subtitle")!.textContent = label[1];
  }),
);
const refreshButton = document.querySelector<HTMLButtonElement>("#refresh")!;
refreshButton.addEventListener("click", async () => {
  if (refreshButton.disabled) return;
  const originalLabel = refreshButton.innerHTML;
  const activeView = document.querySelector<HTMLElement>(".view.active")?.id;
  refreshButton.disabled = true;
  refreshButton.textContent = "Đang làm mới…";
  refreshButton.setAttribute("aria-busy", "true");
  try {
    if (activeView === "conversations") {
      logchatOffset = 0;
      await Promise.all([loadLogChatGateways(), loadChatLogs()]);
    } else if (activeView === "action-sounds") {
      await renderActionSounds();
    } else if (activeView === "background-music") {
      await renderBackgroundMusic();
    } else {
      await load();
    }
  } catch (error) {
    const host = document.querySelector("#logchat-grid");
    if (activeView === "conversations" && host)
      host.innerHTML = `<div class="err" style="margin:14px">${esc(error)}</div>`;
  } finally {
    refreshButton.disabled = false;
    refreshButton.innerHTML = originalLabel;
    refreshButton.removeAttribute("aria-busy");
  }
});
load();

// Ordinary chat lorebook is independent of the Worlds feature flag.
{const nav=document.querySelector(".adminNav");if(nav){const link=document.createElement("a");link.href="/roleplay/lorebook/admin";link.className="btn";link.textContent="Lorebook · Chat thường";nav.appendChild(link);}}
