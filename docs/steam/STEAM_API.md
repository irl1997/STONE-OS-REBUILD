# La interfaz de Steam (cliente 1794536281)

Generado por `dev/steam/steam_api.py report` a partir del código que Valve publica con el cliente (`steam_client_steamrt64` → `steamui_websrc_all`, el cliente de 64 bits que usa la consola). Es la referencia de lo que STONE puede pedirle a Steam: las funciones que la propia interfaz de Steam llama, cuántas veces y con qué argumentos.

## STONE frente a Steam

- ✅ Apps.AddShortcut: as Steam (add_shortcut)
- ✅ Apps.CancelGameAction: as Steam (launch_answer)
- ✅ Apps.ContinueGameAction: as Steam (launch_answer)
- ✅ Apps.GetActiveGameActions: as Steam (launch, launch_answer, launch_state)
- ✅ Apps.GetLaunchOptionsForApp: as Steam (launch, launch_answer, launch_state)
- ⚠️ Apps.GetResolutionOverrideForApp: Steam's interface never calls it; only when present and a game's details do not come: the resolution is read from RegisterForAppDetails (strResolutionOverride), as in Steam's interface (display_default, display_native)
- ✅ Apps.LoadEula: as Steam (accept_eula, install, launch, launch_answer, launch_state)
- ✅ Apps.MarkEulaAccepted: as Steam (accept_eula, launch_answer)
- ✅ Apps.RegisterForAppDetails: as Steam (display_default, display_native, graphics_get)
- ✅ Apps.RegisterForGameActionEnd: as Steam (launch, launch_answer, launch_state)
- ✅ Apps.RegisterForGameActionShowError: as Steam (launch, launch_answer, launch_state)
- ✅ Apps.RegisterForGameActionStart: as Steam (launch, launch_answer, launch_state)
- ✅ Apps.RegisterForGameActionTaskChange: as Steam (launch, launch_answer, launch_state)
- ✅ Apps.RegisterForGameActionUserRequest: as Steam (launch, launch_answer, launch_state)
- ✅ Apps.RemoveShortcut: as Steam (remove_shortcut)
- ✅ Apps.RunGame: as Steam (launch, launch_answer, launch_state, run_game)
- ✅ Apps.SetAppLaunchOptions: as Steam (graphics_set)
- ✅ Apps.SetAppResolutionOverride: as Steam (display_default, display_native)
- ✅ Apps.SetShortcutExe: as Steam (add_shortcut)
- ✅ Apps.SetShortcutLaunchOptions: as Steam (add_shortcut)
- ✅ Apps.SetShortcutName: as Steam (add_shortcut)
- ✅ Apps.SetShortcutStartDir: as Steam (add_shortcut)
- ✅ Apps.TerminateApp: as Steam (terminate)
- ✅ Downloads.EnableAllDownloads: as Steam (download_pause, download_resume)
- ✅ Downloads.ResumeAppUpdate: as Steam (download_pause, download_resume)
- ✅ Installs.CancelInstall: as Steam (accept_eula, cancel_install, install)
- ✅ Installs.ContinueInstall: as Steam (accept_eula, install)
- ⚠️ Installs.GetInstallManagerInfo: Steam's interface never calls it; only when present (feature-tested): the steps come from RegisterForShowInstallWizard, as in Steam's interface; this only finds a wizard left open before STONE asked (accept_eula, install)
- ✅ Installs.OpenInstallWizard: as Steam (accept_eula, install)
- ✅ Installs.OpenUninstallWizard: as Steam (uninstall)
- ✅ Installs.RegisterForShowInstallWizard: as Steam (accept_eula, install)
- ✅ Installs.SetInstallFolder: as Steam (accept_eula, install)
- ✅ System.DisplayManager: as Steam (display_size, display_state)
- ✅ System.DisplayManager.GetState: as Steam (display_state)
- ✅ System.DisplayManager.SetGamescopeInternalResolution: as Steam (display_size)
- ✅ field AddShortcut: occurs in Steam's code
- ✅ field App: occurs in Steam's code
- ✅ field Apps: occurs in Steam's code
- ✅ field BIsModOrShortcut: occurs in Steam's code
- ✅ field BIsOwned: occurs in Steam's code
- ✅ field CancelGameAction: occurs in Steam's code
- ✅ field CancelInstall: occurs in Steam's code
- ✅ field CloseSideMenus: occurs in Steam's code
- ✅ field ContinueGameAction: occurs in Steam's code
- ✅ field ContinueInstall: occurs in Steam's code
- ✅ field DisplayManager: occurs in Steam's code
- ✅ field Downloads: occurs in Steam's code
- ✅ field EnableAllDownloads: occurs in Steam's code
- ✅ field GamepadUIMainWindowInstance: occurs in Steam's code
- ✅ field GetActiveGameActions: occurs in Steam's code
- ✅ field GetClientSetting: occurs in Steam's code
- ✅ field GetFocusedWindowInstance: occurs in Steam's code
- ✅ field GetLaunchOptionsForApp: occurs in Steam's code
- ✅ field GetState: occurs in Steam's code
- ✅ field Installs: occurs in Steam's code
- ✅ field LoadEula: occurs in Steam's code
- ✅ field LocalDownloadOverview: occurs in Steam's code
- ✅ field LocationPathName: occurs in Steam's code
- ✅ field MarkEulaAccepted: occurs in Steam's code
- ✅ field MenuStore: occurs in Steam's code
- ✅ field Navigator: occurs in Steam's code
- ✅ field OpenInstallWizard: occurs in Steam's code
- ✅ field OpenMainMenu: occurs in Steam's code
- ✅ field OpenUninstallWizard: occurs in Steam's code
- ✅ field RegisterForAppDetails: occurs in Steam's code
- ✅ field RegisterForShowInstallWizard: occurs in Steam's code
- ✅ field RemoveShortcut: occurs in Steam's code
- ✅ field ResumeAppUpdate: occurs in Steam's code
- ✅ field RunGame: occurs in Steam's code
- ✅ field SetAppLaunchOptions: occurs in Steam's code
- ✅ field SetAppResolutionOverride: occurs in Steam's code
- ✅ field SetGamescopeInternalResolution: occurs in Steam's code
- ✅ field SetInstallFolder: occurs in Steam's code
- ✅ field SetShortcutExe: occurs in Steam's code
- ✅ field SetShortcutLaunchOptions: occurs in Steam's code
- ✅ field SetShortcutName: occurs in Steam's code
- ✅ field SetShortcutStartDir: occurs in Steam's code
- ✅ field Settings: occurs in Steam's code
- ✅ field SteamClient: occurs in Steam's code
- ✅ field SteamUIStore: occurs in Steam's code
- ✅ field System: occurs in Steam's code
- ✅ field TerminateApp: occurs in Steam's code
- ✅ field WindowStore: occurs in Steam's code
- ✅ field allApps: occurs in Steam's code
- ✅ field allAppsCollection: occurs in Steam's code
- ✅ field allGamesCollection: occurs in Steam's code
- ✅ field appStore: occurs in Steam's code
- ✅ field app_type: occurs in Steam's code
- ✅ field bWaitingForUI: occurs in Steam's code
- ✅ field bytes_downloaded: occurs in Steam's code
- ✅ field bytes_in_progress: occurs in Steam's code
- ✅ field bytes_total: occurs in Steam's code
- ✅ field display_name: occurs in Steam's code
- ✅ field eAppError: occurs in Steam's code
- ✅ field eInstallState: occurs in Steam's code
- ✅ field iInstallFolder: occurs in Steam's code
- ✅ field isArray: occurs in Steam's code
- ✅ field local_per_client_data: occurs in Steam's code
- ✅ field m_CurrentUser: occurs in Steam's code
- ✅ field m_DownloadItems: occurs in Steam's code
- ✅ field m_DownloadOverview: occurs in Steam's code
- ✅ field m_Navigator: occurs in Steam's code
- ✅ field m_mapApps: occurs in Steam's code
- ✅ field minutes_playtime_forever: occurs in Steam's code
- ✅ field nAppID: occurs in Steam's code
- ✅ field nDiskSpaceAvailable: occurs in Steam's code
- ✅ field nDiskSpaceRequired: occurs in Steam's code
- ✅ field nGameActionID: occurs in Steam's code
- ✅ field nIndex: occurs in Steam's code
- ✅ field overall_estimated_time_remaining_sec: occurs in Steam's code
- ✅ field overall_percent_complete: occurs in Steam's code
- ✅ field per_client_data: occurs in Steam's code
- ✅ field queue_index: occurs in Steam's code
- ✅ field rgAppIDs: occurs in Steam's code
- ✅ field rgApps: occurs in Steam's code
- ✅ field rt_last_time_played: occurs in Steam's code
- ✅ field size_on_disk: occurs in Steam's code
- ✅ field strActionName: occurs in Steam's code
- ✅ field strDescription: occurs in Steam's code
- ✅ field strGameName: occurs in Steam's code
- ✅ field strLaunchOptions: occurs in Steam's code
- ✅ field strNumDone: occurs in Steam's code
- ✅ field strNumTotal: occurs in Steam's code
- ✅ field strResolutionOverride: occurs in Steam's code
- ✅ field strSteamID: occurs in Steam's code
- ✅ field strTaskDetails: occurs in Steam's code
- ✅ field strTaskName: occurs in Steam's code
- ✅ field toObject: occurs in Steam's code
- ✅ field update_appid: occurs in Steam's code
- ✅ field update_network_bytes_per_second: occurs in Steam's code
- ✅ field update_state: occurs in Steam's code
- ✅ App.m_CurrentUser: occurs in Steam's code
- ✅ SteamUIStore.GamepadUIMainWindowInstance: occurs in Steam's code
- ✅ SteamUIStore.GetFocusedWindowInstance: occurs in Steam's code
- ✅ SteamUIStore.WindowStore: occurs in Steam's code
- ✅ appStore.allApps: occurs in Steam's code
- ✅ appStore.m_mapApps: occurs in Steam's code
- ✅ collectionStore.allApps: occurs in Steam's code
- ✅ collectionStore.allAppsCollection: occurs in Steam's code
- ✅ collectionStore.allGamesCollection: occurs in Steam's code
- ✅ downloadsStore.LocalDownloadOverview: occurs in Steam's code
- ✅ downloadsStore.get: occurs in Steam's code
- ✅ downloadsStore.m_DownloadItems: occurs in Steam's code
- ✅ downloadsStore.m_DownloadOverview: occurs in Steam's code
- ✅ settingsStore.GetClientSetting: occurs in Steam's code
- ✅ settingsStore.clientSettings: occurs in Steam's code
- ✅ Navigator.Settings('Display'): a settings route of Steam's
- ✅ Navigator.Settings('Audio'): a settings route of Steam's
- ✅ Navigator.Settings('Controller'): a settings route of Steam's
- ✅ Navigator.Settings('Internet'): a settings route of Steam's
- ✅ Navigator.Settings('Bluetooth'): a settings route of Steam's
- ✅ Navigator.Settings('Storage'): a settings route of Steam's
- ✅ Navigator.Settings('System'): a settings route of Steam's
- ✅ Navigator.Settings('Power'): a settings route of Steam's
- ✅ Navigator.Settings('Accessibility'): a settings route of Steam's
- ✅ Navigator.Settings('Keyboard'): a settings route of Steam's
- ✅ Navigator.Settings('Downloads'): a settings route of Steam's
- ✅ Navigator.Downloads(): an entry of Steam's navigator

## Funciones de `SteamClient` que usa la interfaz de Steam

| Función | Veces | Argumentos | Ejemplos de la interfaz de Steam |
| --- | --- | --- | --- |
| `Apps.AddShortcut` | 1 | 4 | `(xe.strAppName,xe.strExePath,xe.strArguments,xe.strCmdline)` |
| `Apps.BackupFilesForApp` | 1 | 2 | `(x,this.state.strFolder)` |
| `Apps.BrowseScreenshotForApp` | 1 | 2 | `(v.strGameID,v.hHandle)` |
| `Apps.CancelBackup` | 1 | 0 | `()` |
| `Apps.CancelGameAction` | 6 | 1 | `(this.m_nGameActionID)` · `(K)` |
| `Apps.CancelLaunch` | 1 | 1 | `(Lt.GetGameID())` |
| `Apps.ClearCustomArtworkForApp` | 2 | 2 | `(this.props.app.appid,this.props.eAssetType)` · `(this.props.overview.appid,it)` |
| `Apps.ClearCustomLogoPositionForApp` | 1 | 1 | `(p.appid)` |
| `Apps.ClearProton` | 1 | 1 | `(g)` |
| `Apps.ContinueGameAction` | 6 | 2 | `(this.m_nGameActionID,Pe)` · `( "+this.m_nGameActionID+", '"+Te+"' )` |
| `Apps.CreateDesktopShortcutForApp` | 2 | 1 | `(ve)` · `(Lt.appid)` |
| `Apps.DownloadWorkshopItem` | 1 | 3 | `(H,q,!0)` |
| `Apps.GetAchievementsInTimeRange` | 1 | 3 | `(P,O,v)` |
| `Apps.GetActiveGameActions` | 1 | 0 | `()` |
| `Apps.GetBackupsInFolder` | 1 | 1 | `(y)` |
| `Apps.GetCloudPendingRemoteOperations` | 1 | 1 | `(p.appid)` |
| `Apps.GetConflictingFileTimestamps` | 1 | 1 | `(p.appid)` |
| `Apps.GetDetailsForScreenshotUpload` | 2 | 2 | `(Se.strGameID,Se.local?.hHandle)` · `(z.strGameID,z.hHandle)` |
| `Apps.GetDetailsForScreenshotUploads` | 1 | 2 | `(At,Y[At])` |
| `Apps.GetDownloadedWorkshopItems` | 1 | 1 | `(H)` |
| `Apps.GetDurationControlInfo` | 1 | 1 | `(this.appid)` |
| `Apps.GetFriendAchievementsForApp` | 1 | 2 | `(T.toString(),R.ConvertTo64BitString())` |
| `Apps.GetGameActionDetails` | 8 | 2 | `(et,Ee=>Fe(Ee.nLaunchOption))` · `(this.m_nGameActionID,this.OnGetGameActionDetails)` |
| `Apps.GetGameActionForApp` | 1 | 2 | `(this.props.overview.GetGameID(),this.onGameActionStart)` |
| `Apps.GetIsSubscribedApp` | 3 | 1 | `(Y)` · `(this.props.unAppID)` |
| `Apps.GetLaunchOptionsForApp` | 9 | 1 | `(Le)` · `(me.appid)` |
| `Apps.GetMyAchievementsForApp` | 1 | 1 | `(T.toString())` |
| `Apps.GetPlaytime` | 1 | 1 | `(this.appid)` |
| `Apps.GetPrePurchasedApps` | 1 | 1 | `(O)` |
| `Apps.GetScreenshotsInTimeRange` | 2 | 3 | `(P.m_unAppID,O,0)` · `(h,0,0)` |
| `Apps.GetShortcutDataForPath` | 1 | 1 | `(ee)` |
| `Apps.GetSoundtrackDetails` | 2 | 1 | `(S)` · `(ae.appid)` |
| `Apps.GetSubscribedWorkshopItemDetails` | 1 | 2 | `(H,V)` |
| `Apps.GetSubscribedWorkshopItems` | 2 | 1 | `(H)` |
| `Apps.InstallFlatpakAppAndCreateShortcut` | 1 | 2 | `(qe,xt)` |
| `Apps.JoinAppContentBeta` | 2 | 2 | `(Yr.unAppID,Ti)` · `(Yr.unAppID,Rr.strName)` |
| `Apps.JoinAppContentBetaByPassword` | 1 | 2 | `(Mi,Yr)` |
| `Apps.LaunchNonSteamApp` | 1 | 1 | `(Wr.strCmdline)` |
| `Apps.ListFlatpakApps` | 2 | 0 | `()` |
| `Apps.LoadEula` | 1 | 1 | `(this.m_AppID)` |
| `Apps.MarkEulaAccepted` | 2 | 3 | `(je,Ke,Ve)` · `(he,oe,Z)` |
| `Apps.MoveWorkshopItemLoadOrder` | 1 | 3 | `(H,q,U)` |
| `Apps.OpenAppSettingsDialog` | 3 | 2 | `(Lt.appid,"")` · `(this.props.app.appid,"updates")` |
| `Apps.RaiseWindowForGame` | 3 | 1 | `(wt)` · `(this.m_gameid)` |
| `Apps.RegisterForAchievementChanges` | 1 | 1 | `(this.OnAchievementChange)` |
| `Apps.RegisterForAppBackupStatus` | 1 | 1 | `(this.OnAppBackupStatus)` |
| `Apps.RegisterForAppDetails` | 1 | 2 | `(p,this.AppDetailsChanged)` |
| `Apps.RegisterForAppOverviewChanges` | 1 | 1 | `(Le=>{this.UpdateAppOverview(Le)&&(this.m_bIsInitialized=!0,Oe&&Oe(),Oe=null)})` |
| `Apps.RegisterForDRMFailureResponse` | 2 | 1 | `(F)` · `(w)` |
| `Apps.RegisterForGameActionEnd` | 2 | 1 | `(this.OnGameActionEnd)` · `(this.onGameActionEnd)` |
| `Apps.RegisterForGameActionShowError` | 1 | 1 | `(this.OnGameActionShowError)` |
| `Apps.RegisterForGameActionShowUI` | 1 | 1 | `(this.OnGameActionShowUI)` |
| `Apps.RegisterForGameActionStart` | 2 | 1 | `(this.OnGameActionStart)` · `(this.onGameActionStart)` |
| `Apps.RegisterForGameActionTaskChange` | 1 | 1 | `(this.OnGameActionTaskChange)` |
| `Apps.RegisterForGameActionUserRequest` | 1 | 1 | `(this.OnGameActionUserRequest)` |
| `Apps.RegisterForPrePurchasedAppChanges` | 1 | 1 | `(()=>this.ScheduleUpdate(0))` |
| `Apps.RegisterForShowMarketingMessageDialog` | 1 | 1 | `(zt)` |
| `Apps.RegisterForShowPendingGiftsDialog` | 1 | 1 | `(zt)` |
| `Apps.RegisterForStatsSchemaChanges` | 1 | 1 | `(this.OnStatsSchemaChange)` |
| `Apps.RegisterForWorkshopChanges` | 1 | 1 | `(this.onWorkshopChanges)` |
| `Apps.RegisterForWorkshopItemDownloads` | 1 | 2 | `(H,this.onWorkshopDownload)` |
| `Apps.RegisterForWorkshopItemInstalled` | 1 | 1 | `(this.onWorkshopItemInstalled)` |
| `Apps.RemoveShortcut` | 1 | 1 | `(Gt)` |
| `Apps.ReportLibraryAssetCacheMiss` | 5 | 2 | `(p,this.props.eAssetType)` · `(Be,G)` |
| `Apps.ReportMarketingMessageDialogShown` | 1 | 0 | `()` |
| `Apps.ReportPendingGiftsDialogShown` | 1 | 0 | `()` |
| `Apps.RequestIconDataForApp` | 1 | 1 | `(Be.appid)` |
| `Apps.RequestLegacyCDKeysForApp` | 1 | 1 | `(F.appid)` |
| `Apps.RunGame` | 2 | 4 | `(C.GetGameID(),"",-1,u.s7X)` · `(Gt.GetGameID(),"",-1,tr)` |
| `Apps.SaveAchievementProgressCache` | 1 | 1 | `(JSON.stringify(this.m_achievementProgress,g))` |
| `Apps.ScanForInstalledNonSteamApps` | 1 | 1 | `(r)` |
| `Apps.SetAppAutoUpdateBehavior` | 2 | 2 | `(Yr.unAppID,Zt.data)` · `(di.unAppID,Xn.data)` |
| `Apps.SetAppBackgroundDownloadsBehavior` | 1 | 2 | `(Yr.unAppID,qi.data)` |
| `Apps.SetAppCurrentLanguage` | 1 | 2 | `(Yr.unAppID,sr.data)` |
| `Apps.SetAppLaunchOptions` | 1 | 2 | `(Yr.unAppID,sr)` |
| `Apps.SetAppResolutionOverride` | 1 | 2 | `(Yr.unAppID,dn.data)` |
| `Apps.SetControllerRumbleIntensity` | 1 | 2 | `(Yr.unAppID,ci.data)` |
| `Apps.SetCustomArtworkForApp` | 3 | 4 | `(this.props.app.appid,q,k,this.props.eAssetType)` · `(qe,Si,Er,xt)` |
| `Apps.SetCustomLogoPositionForApp` | 1 | 2 | `(p.appid,JSON.stringify(k))` |
| `Apps.SetDLCEnabled` | 1 | 3 | `(Yr,Vr.unAppID,sr)` |
| `Apps.SetFDMEnable` | 1 | 2 | `(Yr.unAppID,Ai)` |
| `Apps.SetForceIdentAsSteamDeck` | 1 | 2 | `(Yr.unAppID,Zt)` |
| `Apps.SetLocalScreenshotCaption` | 2 | 3 | `(je.local.strGameID,je.local.hHandle,Ke\|\|"")` · `(z.strGameID,z.hHandle,p.strCaption)` |
| `Apps.SetLocalScreenshotPrivacy` | 1 | 3 | `(je.local.strGameID,je.local.hHandle,Ve)` |
| `Apps.SetLocalScreenshotSpoiler` | 2 | 3 | `(je.local.strGameID,je.local.hHandle,Ke)` · `(z.strGameID,z.hHandle,p.bSpoiler)` |
| `Apps.SetRPOEnable` | 1 | 2 | `(Yr.unAppID,Ai)` |
| `Apps.SetShortcutExe` | 2 | 2 | `(Yr,(0,j.yd)(qi))` · `(Yr,qi)` |
| `Apps.SetShortcutIcon` | 1 | 2 | `(Yr,Ji)` |
| `Apps.SetShortcutIsVR` | 1 | 2 | `(Yr,!sr.bShortcutIsVR)` |
| `Apps.SetShortcutLaunchOptions` | 1 | 2 | `(Yr,qi)` |
| `Apps.SetShortcutName` | 1 | 2 | `(Yr,qi)` |
| `Apps.SetShortcutSortAs` | 1 | 2 | `(Be,ze)` |
| `Apps.SetShortcutStartDir` | 2 | 2 | `(Yr,qi)` |
| `Apps.SetStreamingClientForApp` | 1 | 2 | `(this.props.overview.appid,it.clientid)` |
| `Apps.SetTSOEnable` | 1 | 2 | `(Yr.unAppID,dn.data)` |
| `Apps.SetThirdPartyControllerConfiguration` | 3 | 2 | `(Bi,H.gG)` · `(Bi,Gi?H.Dt:H.pg)` |
| `Apps.SetWorkshopItemsDisabledLocally` | 2 | 3 | `(Yr,[Yi],ei)` · `(Yr.unAppID,yr,!ur)` |
| `Apps.SetWorkshopItemsLoadOrder` | 1 | 2 | `(H,he)` |
| `Apps.ShowControllerConfigurator` | 12 | 1 | `(A.qho)` · `(r.mZ)` |
| `Apps.ShowStore` | 2 | 1 | `(Lt.appid)` · `(Gt.appid)` |
| `Apps.SpecifyCompatExperiment` | 3 | 2 | `(Yr.unAppID,Ai(mi))` · `(Yr.unAppID,"")` |
| `Apps.StreamGame` | 3 | 3 | `(j.g5s,ci.clientId,-1)` · `(o.g5s,oe,-1)` |
| `Apps.SubscribeWorkshopItem` | 3 | 3 | `(H,q,!0)` · `(H,q,!1)` |
| `Apps.TerminateApp` | 6 | 2 | `(Er,!1)` · `(U,!1)` |
| `Apps.ToggleAllowDesktopConfiguration` | 1 | 1 | `(Yr.unAppID)` |
| `Apps.ToggleAppSteamCloudEnabled` | 1 | 1 | `(Yr.unAppID)` |
| `Apps.ToggleAppSteamCloudSyncOnSuspendEnabled` | 1 | 1 | `(Yr.unAppID)` |
| `Apps.ToggleEnableSteamOverlayForApp` | 2 | 1 | `(Yr.unAppID)` · `(sr.unAppID)` |
| `Apps.ToggleOverrideResolutionForInternalDisplay` | 1 | 1 | `(Yr.unAppID)` |
| `Apps.VerifyApp` | 1 | 1 | `(N)` |
| `Auth.ClearCachedSignInPin` | 1 | 0 | `()` |
| `Auth.CurrentUserHasCachedSignInPin` | 1 | 0 | `()` |
| `Auth.GetLocalHostname` | 3 | 0 | `()` |
| `Auth.GetMachineID` | 1 | 0 | `()` |
| `Auth.GetRefreshInfo` | 2 | 0 | `()` |
| `Auth.GetSteamGuardData` | 2 | 1 | `(Ae)` · `(vr)` |
| `Auth.IsSecureComputer` | 1 | 0 | `()` |
| `Auth.SetCachedSignInPin` | 1 | 1 | `(wr)` |
| `Auth.SetLoginToken` | 2 | 2 | `(nr.strRefreshToken,nr.strAccountName)` · `(Xe.strRefreshToken,Xe.strAccountName)` |
| `Auth.SetSteamGuardData` | 2 | 2 | `(nr.strAccountName,zt)` · `(Xe.strAccountName,Se)` |
| `Auth.StartSignInFromCache` | 1 | 1 | `(tr)` |
| `Auth.ValidateCachedSignInPin` | 1 | 2 | `(tr.strAccountName,yt)` |
| `Downloads.EnableAllDownloads` | 5 | 2 | `(!1,ve.clientid)` · `(Ct,m.hj.CurrentViewingRemoteClientID)` |
| `Downloads.PauseAppUpdate` | 1 | 2 | `(ot,m.hj.CurrentViewingRemoteClientID)` |
| `Downloads.QueueAppUpdate` | 1 | 2 | `(zt,m.hj.CurrentViewingRemoteClientID)` |
| `Downloads.RegisterForDownloadItems` | 1 | 1 | `(this.OnDownloadItems)` |
| `Downloads.RegisterForDownloadOverview` | 1 | 1 | `(this.OnDownloadOverview)` |
| `Downloads.RegisterForRemoteClientsConnected` | 1 | 1 | `(this.OnRemoteClientsChanged)` |
| `Downloads.RemoveFromDownloadList` | 2 | 2 | `(Lt.appid,m.hj.CurrentViewingRemoteClientID)` |
| `Downloads.ResumeAppUpdate` | 3 | 2 | `(Lt.appid,ve.clientid)` · `(W.appid,r.Oy)` |
| `Downloads.SetLaunchOnUpdateComplete` | 1 | 1 | `(tr.launch_on_completion?O.sc:tr.appid)` |
| `Downloads.SetQueueIndex` | 1 | 3 | `(ot,vt.destination.index,m.hj.CurrentViewingRemoteClientID)` |
| `Downloads.SuspendDownloadThrottling` | 1 | 2 |  |
| `Downloads.SuspendLanPeerContent` | 1 | 2 | `(!0,m.hj.CurrentViewingRemoteClientID)` |
| `GameSessions.RegisterForAchievementNotification` | 3 | 1 | `(this.OnAchievementNotification)` |
| `GameSessions.RegisterForAppLifetimeNotifications` | 2 | 1 | `(this.OnAppLifetimeNotification)` |
| `GameSessions.RegisterForScreenshotNotification` | 3 | 1 | `(this.OnScreenshotNotification)` |
| `Installs.CancelInstall` | 8 | 0 | `()` |
| `Installs.ContinueInstall` | 4 | 0 | `()` |
| `Installs.OpenInstallBackup` | 1 | 1 | `(this.state.strFolder)` |
| `Installs.OpenInstallWizard` | 4 | 2 | `([Number(et)],o.Oy)` · `([N],K)` |
| `Installs.OpenUninstallWizard` | 2 | 3 | `([O.unAppID],a.Oy,!0)` · `(f,D,!0)` |
| `Installs.RegisterForShowConfirmUninstall` | 1 | 1 | `(this.OnShowConfirmUninstall)` |
| `Installs.RegisterForShowFailedUninstall` | 1 | 1 | `(this.OnShowFailedUninstall)` |
| `Installs.RegisterForShowInstallWizard` | 1 | 1 | `(this.OnShowInstallWizard)` |
| `Installs.SetCreateShortcuts` | 1 | 2 | `(N,K)` |
| `Installs.SetInstallFolder` | 2 | 1 | `(N)` |
| `Overlay.DestroyGamePadUIDesktopConfiguratorWindow` | 5 | 0 | `()` |
| `Overlay.GetOverlayBrowserInfo` | 1 | 0 | `()` |
| `Overlay.HandleGameWebCallback` | 1 | 1 | `(g)` |
| `Overlay.HandleProtocolForOverlayBrowser` | 1 | 2 | `(this.m_unAppID,g)` |
| `Overlay.RegisterForActivateOverlayRequests` | 1 | 1 | `(this.OnGameOverlayActivateRequested)` |
| `Overlay.RegisterForMicroTxnAuth` | 2 | 1 | `(this.OnMicroTxnAuth)` · `(wi)` |
| `Overlay.RegisterForMicroTxnAuthDismiss` | 2 | 1 | `(this.OnMicroTxnAuthDismiss)` · `(hn)` |
| `Overlay.RegisterForNotificationPositionChanged` | 1 | 1 | `(this.OverlayNotificationPositionChanged)` |
| `Overlay.RegisterForOverlayActivated` | 2 | 1 | `(f)` · `(this.OnOverlayActivated)` |
| `Overlay.RegisterForOverlayBrowserProtocols` | 1 | 1 | `(this.OnOverlayBrowserProtocol)` |
| `Overlay.RegisterOverlayBrowserInfoChanged` | 1 | 1 | `(this.OnOverlayBrowserInfoChanged)` |
| `Overlay.SetOverlayState` | 16 | 2 | `(C.gameid,s.I5.Hidden)` · `(C.gameid,U)` |
| `Overlay.SetWindowAlpha` | 2 | 1 | `(Cr)` · `(1)` |
| `Overlay.SetWindowPinned` | 1 | 1 | `(!ar)` |
| `Settings.AddClientBeta` | 1 | 2 | `(Yt,de)` |
| `Settings.ClearAllHTTPCaches` | 1 | 0 | `()` |
| `Settings.ClearDownloadCache` | 1 | 0 | `()` |
| `Settings.GetAccountSettings` | 2 | 0 | `()` |
| `Settings.GetAppUsesP2PVoice` | 1 | 1 | `(Xn??0)` |
| `Settings.GetAvailableLanguages` | 2 | 0 | `()` |
| `Settings.GetAvailableTimeZones` | 2 | 0 | `()` |
| `Settings.GetCurrentLanguage` | 2 | 0 | `()` |
| `Settings.GetMonitorInfo` | 1 | 0 | `()` |
| `Settings.GetRegisteredSteamDeck` | 1 | 0 | `()` |
| `Settings.GetTimeZone` | 1 | 0 | `()` |
| `Settings.GetWindowed` | 1 | 0 | `()` |
| `Settings.IgnoreSteamDeckRewards` | 1 | 0 | `()` |
| `Settings.OpenWindowsMicSettings` | 1 | 0 | `()` |
| `Settings.RegisterForAppsWithAutoUpdateOverrides` | 1 | 1 | `(gi=>Lr(gi.map(di=>di.appid)))` |
| `Settings.RegisterForMicVolumeUpdates` | 1 | 1 | `(Lr)` |
| `Settings.RegisterForSettingsArrayChanges` | 1 | 1 | `(this.OnClientSettingsMsgChange)` |
| `Settings.RegisterForSettingsChanges` | 1 | 1 | `(this.OnClientSettingsChange)` |
| `Settings.RegisterForTimeZoneChange` | 2 | 1 | `(d)` · `(this.OnTimeZoneChange)` |
| `Settings.ReinitMicSettings` | 1 | 0 | `()` |
| `Settings.RenderHotkey` | 1 | 1 | `(oe)` |
| `Settings.SelectClientBeta` | 6 | 1 | `(P.nBetaID)` · `(O.nBetaID)` |
| `Settings.SetCurrentLanguage` | 2 | 1 | `(P.strShortName)` · `(re)` |
| `Settings.SetEnableSoftProcessKill` | 1 | 1 | `(It)` |
| `Settings.SetHostname` | 1 | 1 | `(Ot)` |
| `Settings.SetMicTestMode` | 1 | 1 | `(jn)` |
| `Settings.SetPreferredMonitor` | 1 | 1 | `(le)` |
| `Settings.SetRegisteredSteamDeck` | 2 | 2 | `(i.iA.steamid,N)` |
| `Settings.SetSaveAccountCredentials` | 1 | 1 | `(!gi)` |
| `Settings.SetSetting` | 1 | 1 | `(G)` |
| `Settings.SetTimeZone` | 2 | 1 | `(P)` · `(I)` |
| `Settings.SetUseNintendoButtonLayout` | 1 | 2 | `(be.nControllerIndex,mt)` |
| `Settings.SetUseUniversalFaceButtonGlyphs` | 1 | 2 | `(be.nControllerIndex,nr)` |
| `Settings.SetWindowed` | 1 | 1 | `(le)` |
| `Settings.ToggleSteamInstall` | 1 | 0 | `()` |
| `Storage.DeleteKey` | 2 | 1 | `(z)` · `(o)` |
| `Storage.GetString` | 2 | 1 | `(z)` · `(o)` |
| `Storage.SetString` | 3 | 2 | `(z,f)` · `(o,n)` |
| `System.Audio` | 1 | — |  |
| `System.Audio.ClearDefaultDeviceOverride` | 1 | 1 | `(re)` |
| `System.Audio.GetApps` | 1 | 0 | `()` |
| `System.Audio.GetDevices` | 3 | 0 | `()` |
| `System.Audio.RegisterForAppAdded` | 1 | 1 | `(this.OnAppAdded)` |
| `System.Audio.RegisterForAppRemoved` | 1 | 1 | `(this.OnAppRemoved)` |
| `System.Audio.RegisterForAppVolumeChanged` | 1 | 1 | `(this.OnAppVolumeChanged)` |
| `System.Audio.RegisterForDeviceAdded` | 1 | 1 | `(this.OnAudioDeviceAdded)` |
| `System.Audio.RegisterForDeviceRemoved` | 1 | 1 | `(this.OnAudioDeviceRemoved)` |
| `System.Audio.RegisterForDeviceVolumeChanged` | 1 | 1 | `(this.OnAudioDeviceVolumeChanged)` |
| `System.Audio.RegisterForServiceConnectionStateChanges` | 1 | 1 | `(this.OnServiceConnectionStateChanged)` |
| `System.Audio.RegisterForVolumeButtonPressed` | 1 | 1 | `(this.OnVolumeButtonPressed)` |
| `System.Audio.SetAppVolume` | 1 | 2 | `(this.id,re)` |
| `System.Audio.SetDefaultDeviceOverride` | 1 | 2 | `(this.m_id,re)` |
| `System.Audio.SetDeviceVolume` | 1 | 3 | `(this.m_id,re,Ie)` |
| `System.AudioDevices.RegisterForStateChanges` | 1 | 1 | `(this.OnStateChanged)` |
| `System.AudioDevices.UpdateSomething` | 2 | 1 | `(ke.serializeBase64String())` · `(nt.serializeBase64String())` |
| `System.CopyFile` | 2 | 2 | `(mt,$t)` · `(te,Be)` |
| `System.CopyFilesToClipboard` | 4 | 1 | `(Tr.filter(Boolean))` · `([Es.strExportPath])` |
| `System.CreateTempPath` | 3 | 1 | `(Dt)` · `(v)` |
| `System.Devkit.RegisterForPairingPrompt` | 1 | 1 | `(this.OnPairingPrompt)` |
| `System.Devkit.RespondToPairingPrompt` | 1 | 2 | `(nt,ke)` |
| `System.Devkit.SetPairing` | 1 | 1 | `(nt)` |
| `System.Display.EnableUnderscan` | 4 | 1 | `(!H)` · `(!K)` |
| `System.Display.RegisterForBrightnessChanges` | 1 | 1 | `(this.OnDisplayBrightnessChanged)` |
| `System.Display.SetBrightness` | 1 | 1 | `(v)` |
| `System.Display.SetUnderscanLevel` | 3 | 1 | `(G)` · `(N)` |
| `System.DisplayManager` | 1 | — |  |
| `System.DisplayManager.ClearModeOverride` | 1 | 1 | `(z)` |
| `System.DisplayManager.GetState` | 2 | 0 | `()` |
| `System.DisplayManager.RegisterForStateChanges` | 1 | 1 | `(this.OnStateChanged)` |
| `System.DisplayManager.SetCompatibilityMode` | 1 | 1 | `(z)` |
| `System.DisplayManager.SetGamescopeInternalResolution` | 1 | 2 | `(z,U/N==1.6?z/1.6:p)` |
| `System.DisplayManager.SetMode` | 1 | 1 | `(k.serializeBase64String())` |
| `System.Dock.DisarmSafetyNet` | 1 | 0 | `()` |
| `System.Dock.RegisterForStateChanges` | 1 | 1 | `(this.OnStateChanged)` |
| `System.Dock.UpdateFirmware` | 1 | 1 | `(b.serializeBase64String())` |
| `System.FormatStorage` | 1 | 1 | `(We)` |
| `System.GetOSType` | 2 | 0 | `()` |
| `System.GetSystemInfo` | 2 | 0 | `()` |
| `System.IsDeckFactoryImage` | 1 | 0 | `()` |
| `System.IsSteamInTournamentMode` | 2 | 0 | `()` |
| `System.Network.Device` | 5 | — |  |
| `System.Network.ForceTestConnectivity` | 1 | 0 | `()` |
| `System.Network.GetProxyInfo` | 1 | 0 | `()` |
| `System.Network.RegisterForAppSummaryUpdate` | 1 | 1 | `(Je)` |
| `System.Network.RegisterForConnectionStateUpdate` | 1 | 1 | `(pe)` |
| `System.Network.RegisterForConnectivityTestChanges` | 1 | 1 | `(this.OnConnectivityTestStateChanged)` |
| `System.Network.RegisterForDeviceChanges` | 1 | 1 | `(this.OnNetworkDevicesChanged)` |
| `System.Network.SetFakeLocalSystemState` | 1 | 1 | `(Ze)` |
| `System.Network.SetProxyInfo` | 1 | 4 | `(Ze.proxy_mode,Ze.address??"",Ze.port??0,Ze.exclude_local??!0)` |
| `System.Network.SetWifiEnabled` | 1 | 1 | `(Ze)` |
| `System.Network.StartScanningForNetworks` | 1 | 0 | `()` |
| `System.Network.StopScanningForNetworks` | 1 | 0 | `()` |
| `System.NotifyGameOverlayStateChanged` | 1 | 2 | `(v,P)` |
| `System.OpenFileDialog` | 12 | 1 | `({strTitle:(0,o.we)("#AddNonSteam_PickAppTitle"),rgFilters:f(),strInitialFile:P})` · `({strTitle:(0,d.we)("#MediaManager_SaveDialogTitle"),bChooseDirectory:!0})` |
| `System.OpenInSystemBrowser` | 3 | 1 | `(h)` · `(cr)` |
| `System.OpenLocalDirectoryInSystemExplorer` | 5 | 1 | `(Lt.strShortcutStartDir)` · `(Lt.strInstallFolder)` |
| `System.Perf.RegisterForDiagnosticInfoChanges` | 1 | 1 | `(this.OnDiagnosticInfoChanged)` |
| `System.Perf.RegisterForStateChanges` | 1 | 1 | `(this.OnStateChanged)` |
| `System.Perf.UpdateSettings` | 26 | 1 | `(ce.serializeBase64String())` · `(xe.serializeBase64String())` |
| `System.RebootToAlternateSystemPartition` | 2 | 0 | `()` |
| `System.RegisterForAirplaneModeChanges` | 1 | 1 | `(this.OnAirplaneModeChanged)` |
| `System.RegisterForBatteryStateChanges` | 1 | 1 | `(this.OnBatteryStateChanged)` |
| `System.RegisterForFormatStorageProgress` | 1 | 1 | `(this.OnFormatStorageProgress)` |
| `System.RegisterForSettingsChanges` | 1 | 1 | `(this.OnSettingsChanged)` |
| `System.RestartPC` | 8 | 0 | `()` |
| `System.SetAirplaneMode` | 1 | 1 | `(v)` |
| `System.ShutdownPC` | 1 | 0 | `()` |
| `System.SteamRuntimeSystemInfo` | 1 | 0 | `()` |
| `System.SuspendPC` | 1 | 0 | `()` |
| `System.UI.CloseGameWindow` | 1 | 2 | `(fe,Xt)` |
| `System.UI.GetGameWindowsInfo` | 1 | 2 | `(fe,Xt)` |
| `System.UI.RegisterForFocusChangeEvents` | 3 | 1 | `(this.OnFocusChangeEvent)` |
| `System.UI.RegisterForOverlayGameWindowFocusChanged` | 1 | 1 | `(this.OnOverlayGameWindowFocusChanged)` |
| `System.UI.RegisterForSystemKeyEvents` | 2 | 1 | `(this.HandleSystemKeyEvents)` · `(this.HandleGamepadGuideButtonEvents)` |
| `System.UpdateSettings` | 17 | 1 | `(z.serializeBase64String())` · `(v.serializeBase64String())` |
| `System.VideoRecordingDriverCheck` | 1 | 0 | `()` |
| `UI.EnsureMainWindowCreated` | 1 | 0 | `()` |
| `UI.ExitBigPictureMode` | 3 | 0 | `()` |
| `UI.GetDesiredSteamUIWindows` | 1 | 0 | `()` |
| `UI.GetOSEndOfLifeInfo` | 1 | 0 | `()` |
| `UI.GetUIMode` | 2 | 0 | `()` |
| `UI.NotifyAppInitialized` | 2 | 0 | `()` |
| `UI.NotifyMainWindowShown` | 2 | 0 | `()` |
| `UI.RegisterDesiredSteamUIWindowsChanged` | 1 | 1 | `(this.OnDesiredSteamUIWindowsChanged)` |
| `UI.RegisterForClientConVar` | 1 | 2 |  |
| `UI.RegisterForDifferentLauncherRequested` | 1 | 1 | `(this.OnDifferentLauncherRequested)` |
| `UI.RegisterForErrorCondition` | 1 | 1 | `(this.OnErrorCondition)` |
| `UI.RegisterForKioskModeResetSignal` | 1 | 1 | `(this.OnKioskModeReset)` |
| `UI.RegisterForStartupFinished` | 1 | 1 | `(()=>{K(),V.unregister()})` |
| `UI.RegisterForUIModeChanged` | 3 | 1 | `(K=>{this.EnsureCurrentRouteAllowed()})` · `(this.OnUIModeChanged)` |
| `UI.RegisterMoveGamepadUIMainWindowToPrimaryDisplay` | 1 | 1 | `(this.OnMoveGamepadUIMainWindowToPrimaryDisplay)` |
| `UI.ResetErrorCondition` | 1 | 0 | `()` |
| `UI.SetUIMode` | 4 | 1 | `(a.$l2)` · `(a.ogI)` |
| `User.AuthorizeMicrotxn` | 1 | 1 | `(this.m_gidTransID)` |
| `User.CancelMicrotxn` | 1 | 1 | `(this.m_gidTransID)` |
| `User.CancelShutdown` | 1 | 0 | `()` |
| `User.Connect` | 1 | 0 | `()` |
| `User.ForceShutdown` | 1 | — |  |
| `User.ForgetPassword` | 1 | 1 | `(F)` |
| `User.GetLoginUsers` | 2 | 0 | `()` |
| `User.GetStartupUserChooserState` | 2 | 0 | `()` |
| `User.GoOffline` | 2 | 0 | `()` |
| `User.GoOnline` | 2 | 0 | `()` |
| `User.OnCloseSaveHardwareDialog` | 2 | 0 | `()` |
| `User.OptOutOfSurvey` | 1 | 0 | `()` |
| `User.PrepareForSystemSuspend` | 1 | 0 | `()` |
| `User.Reconnect` | 1 | 0 | `()` |
| `User.RegisterForConnectionAttemptsThrottled` | 1 | 1 | `(this.OnConnectionAttemptThrottled)` |
| `User.RegisterForCurrentUserChanges` | 1 | 1 | `(this.OnCurrentUserChanges)` |
| `User.RegisterForLoginStateChange` | 3 | 1 | `(this.OnLoginStateChange)` |
| `User.RegisterForLoginUsersChanged` | 1 | 1 | `(this.OnLoginUsersChanged)` |
| `User.RegisterForPrepareForSystemSuspendProgress` | 1 | 1 | `(this.OnPrepareForSuspendProgress)` |
| `User.RegisterForResumeSuspendedGamesProgress` | 1 | 1 | `(this.OnResumeSuspendedGamesProgress)` |
| `User.RegisterForShowHardwareSurvey` | 1 | 1 | `(z)` |
| `User.RegisterForShutdownDone` | 1 | 1 | `(this.OnShutdownDone)` |
| `User.RegisterForShutdownFailed` | 1 | 1 | `(this.OnShutdownFailed)` |
| `User.RegisterForShutdownStart` | 1 | 1 | `(this.OnShutdownStart)` |
| `User.RegisterForShutdownState` | 1 | 1 | `(this.OnShutdownState)` |
| `User.RegisterShowSaveHardwareDialog` | 1 | 1 | `(oe)` |
| `User.RemoveAllUsers` | 1 | 0 | `()` |
| `User.RemoveUser` | 1 | 1 | `(g)` |
| `User.RequestSupportSystemReport` | 1 | 1 | `(R)` |
| `User.RestartAsUser` | 2 | 1 | `(F)` · `(I)` |
| `User.RestartToLoginScreen` | 2 | 0 | `()` |
| `User.RestartToUserChooser` | 2 | 0 | `()` |
| `User.ResumeSuspendedGames` | 2 | 1 | `(!1)` · `(!0)` |
| `User.RunSurvey` | 3 | 1 | `(P)` · `(z)` |
| `User.SendSurvey` | 1 | 0 | `()` |
| `User.SetAsyncNotificationEnabled` | 2 | 2 | `(Le.request.appid,!0)` · `(Le.request.appid,!1)` |
| `User.SetCheckForUpdatesOnRestart` | 1 | 1 | `(!0)` |
| `User.SetLoginCredentials` | 1 | 3 | `(D,y,E)` |
| `User.SetRestartArgs` | 1 | 1 | `(h)` |
| `User.ShowSaveHardwareDialog` | 2 | 0 | `()` |
| `User.SignOutAndRestart` | 1 | 0 | `()` |
| `User.StartLogin` | 2 | 0 | `()` |
| `User.StartOffline` | 1 | 1 | `(!0)` |
| `User.StartRestart` | 15 | 1 | `(!1)` · `(!0)` |
| `User.StartShutdown` | 8 | 1 | `(!0)` |
| `Window.BringToFront` | 32 | 0, 1 | `()` · `(z)` |
| `Window.Close` | 3 | 0 | `()` |
| `Window.DefaultMonitorHasFullscreenWindow` | 1 | 0 | `()` |
| `Window.GetDefaultMonitorDimensions` | 1 | 0 | `()` |
| `Window.GetMousePositionDetails` | 1 | 0 | `()` |
| `Window.GetWindowDetails` | 1 | 0 | `()` |
| `Window.GetWindowDimensions` | 3 | 0 | `()` |
| `Window.GetWindowRestoreDetails` | 7 | 0 | `()` |
| `Window.HideWindow` | 13 | 0 | `()` |
| `Window.IsWindowMaximized` | 2 | 0 | `()` |
| `Window.IsWindowMinimized` | 2 | 0 | `()` |
| `Window.MarkLastFocused` | 2 | 0 | `()` |
| `Window.Minimize` | 4 | 0 | `()` |
| `Window.MoveTo` | 7 | 3 | `(this.state.menuLeft,this.state.menuTop,le??!0)` · `(0,0,!1)` |
| `Window.MoveToLocation` | 3 | 1, 2, 3 | `(this.KeyboardLocation,this.k_nKeyboardWindowOffset)` · `("upper-left",0,pe.strMonitorDeviceName)` |
| `Window.PositionWindowRelative` | 5 | 5 | `(p,z.left,z.top,z.width,z.height)` · `(y,x,E,this.state.width,this.state.height)` |
| `Window.ProcessShuttingDown` | 1 | 0 | `()` |
| `Window.ResizeTo` | 12 | 3 | `(1280,Bt.innerHeight,!1)` · `(la.UIDisplayPrefs.nFriendsListSingleWindowWidthPx,Bt.innerHeight,!1)` |
| `Window.RestoreWindowSizeAndPosition` | 1 | 1 | `(hr.strRestoreDetails)` |
| `Window.SetComposition` | 1 | 3 | `(z,p,k)` |
| `Window.SetGamepadUIAutoDisplayScale` | 2 | 1 | `(q)` · `(!0)` |
| `Window.SetGamepadUIManualDisplayScaleFactor` | 3 | 1 | `(oe)` · `(q)` |
| `Window.SetHideOnClose` | 5 | 1 | `(!1)` · `(!!g.bHideOnClose)` |
| `Window.SetKeyFocus` | 4 | 1 | `( true )` · `(!0)` |
| `Window.SetMinSize` | 9 | 2 | `(Es.KO,Es.rS)` · `(Es.Y$,Es.rS)` |
| `Window.SetModal` | 2 | 1 | `(!0)` · `(!1)` |
| `Window.SetResizeGrip` | 2 | 2 | `(g,m)` · `(0,0)` |
| `Window.SetWindowFlashing` | 1 | 1 | `(Mr)` |
| `Window.SetWindowIcon` | 7 | 1 | `("voice")` · `("messages")` |
| `Window.ShowWindow` | 14 | 0 | `()` |
| `Window.ToggleFullScreen` | 3 | 1 | `(!le)` · `(!0)` |
| `Window.ToggleMaximize` | 1 | 0 | `()` |

## Almacenes en `window`

`App`, `BrowserAndBackstackInstances`, `ControllerStore`, `DEBUG_GetDesiredSteamUIWindows`, `DEBUG_SuppressWindowType`, `FocusNavController`, `FocusedAppWindowStore`, `LocalizationManager`, `MainWindowBrowserManager`, `NotificationStore`, `RemotePlayStore_SteamUI`, `ResetNewContentRollup`, `SetHoverPresentation`, `SetVoiceAutoShowVideoStream`, `SetVoiceEchoLocalMic`, `SetVoiceForceConnectingStatus`, `SetVoiceForceReconnectingStatus`, `SetVoiceLogDetails`, `ShowContentReportDialog`, `ShowVROverlay`, `SteamUIStore`, `SuspendResumeStore`, `SystemAudioDevicesStore`, `SystemDevkitStore`, `SystemDisplayManagerStore`, `SystemDockStore`, `SystemNetworkStore`, `SystemPerfStore`, `SystemPowerStore`, `SystemReportStore`, `SystemStoragStore`, `UpdateStore`, `VRPathProperties`, `appAchievementProgressCache`, `appActivityStore`, `appDetailsCache`, `appDetailsStore`, `appInfoStore`, `appReviewStore`, `appSpotlightStore`, `appStore`, `badgeStore`, `cloudStorage`, `cloudStorageInternalState`, `cm`, `collectionStore`, `communityStore`, `consoleStore`, `controllerConfiguratorStore`, `downloadsStore`, `dragStore`, `friendStore`, `g_FriendsUIApp`, `g_GRS`, `g_LogManager`, `g_PopupManager`, `g_SubscriptionStore`, `g_WindowFocusCoordinator`, `gameReleaseStore`, `hardwarePromoStore`, `installFolderStore`, `jsonit`, `libraryEventStore`, `loginStore`, `multiSelectStore`, `onYouTubeIframeAPIReady`, `overlayStore`, `partnerEventStore`, `playNextStore`, `protoPathProperties`, `screenshotStore`, `searchstore`, `securitystore`, `serverBrowserStore`, `settingsStore`, `settingsZooStore`, `showcaseStore`, `steamAjaxRequest`, `streamingStore`, `subscriberAgreementStore`, `tempNavStore`, `toJS`, `trendingStore`, `uiBroadcastWatchStore`, `uiStore`, `urlStore`, `userProfileStore`, `vrAudioSettingsStore`, `vrFrameStore`, `vrGamepadInput`, `vrPooledPopupStore`, `workshopStore`

## Enumeraciones que STONE usa

- `k_EInstallMgrState`: one = 0, etup = 1, aitLicense = 2, reeLicense = 3, howCDKey = 4, aitAppInfo = 5, howPassword = 6, howConfig = 7, howEULAs = 8, reateApps = 9, eadFromMedia = 10, howChangeMedia = 11, aitLegacyCDKeys = 12, howSignup = 13, omplete = 14, ailed = 15, anceled = 16
- `k_EAppUpdateProgress`: VerifyingInstalledFiles = 0, Preallocating = 1, Download = 2, Staging = 3, VerifyingStagedFiles = 4, Copying = 5, Committing = 6, Max = 7
- `k_ELaunchOptionType`: None = 0, Default = 1, SafeMode = 2, Multiplayer = 3, Config = 4, OpenVR = 5, Server = 6, Editor = 7, Manual = 8, Benchmark = 9, Option1 = 10, Option2 = 11, Option3 = 12, OculusVR = 13, OpenVROverlay = 14, OSVR = 15, OpenXR = 16
