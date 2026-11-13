# La interfaz de Steam (cliente 1792618285)

Generado por `dev/steam/steam_api.py report` a partir del código que Valve publica con el cliente (`steam_client_ubuntu12` → `steamui_websrc_all`). Es la referencia de lo que STONE puede pedirle a Steam: las funciones que la propia interfaz de Steam llama, cuántas veces y con qué argumentos.

## STONE frente a Steam

- ✅ Apps.AddShortcut: as Steam (add_shortcut)
- ✅ Apps.CancelGameAction: as Steam (launch_answer)
- ✅ Apps.ContinueGameAction: as Steam (launch_answer)
- ✅ Apps.GetActiveGameActions: as Steam (launch, launch_answer, launch_state)
- ✅ Apps.GetLaunchOptionsForApp: as Steam (launch, launch_answer, launch_state)
- ✅ Apps.LoadEula: as Steam (accept_eula, install, launch, launch_answer, launch_state)
- ✅ Apps.MarkEulaAccepted: as Steam (accept_eula, launch_answer)
- ✅ Apps.RegisterForGameActionEnd: as Steam (launch, launch_answer, launch_state)
- ✅ Apps.RegisterForGameActionShowError: as Steam (launch, launch_answer, launch_state)
- ✅ Apps.RegisterForGameActionStart: as Steam (launch, launch_answer, launch_state)
- ✅ Apps.RegisterForGameActionTaskChange: as Steam (launch, launch_answer, launch_state)
- ✅ Apps.RegisterForGameActionUserRequest: as Steam (launch, launch_answer, launch_state)
- ✅ Apps.RunGame: as Steam (launch, launch_answer, launch_state, run_game)
- ✅ Apps.SetShortcutName: as Steam (add_shortcut)
- ✅ Installs.CancelInstall: as Steam (accept_eula, cancel_install, install)
- ✅ Installs.ContinueInstall: as Steam (accept_eula, install)
- ⚠️ Installs.GetInstallManagerInfo: Steam's interface never calls it; only when present (feature-tested): the steps come from RegisterForShowInstallWizard, as in Steam's interface; this only finds a wizard left open before STONE asked (accept_eula, install)
- ✅ Installs.OpenInstallWizard: as Steam (accept_eula, install)
- ✅ Installs.OpenUninstallWizard: as Steam (uninstall)
- ✅ Installs.RegisterForShowInstallWizard: as Steam (accept_eula, install)
- ✅ Installs.SetInstallFolder: as Steam (accept_eula, install)
- ✅ field AddShortcut: occurs in Steam's code
- ✅ field App: occurs in Steam's code
- ✅ field Apps: occurs in Steam's code
- ✅ field BIsModOrShortcut: occurs in Steam's code
- ✅ field CancelGameAction: occurs in Steam's code
- ✅ field CancelInstall: occurs in Steam's code
- ✅ field CloseSideMenus: occurs in Steam's code
- ✅ field ContinueGameAction: occurs in Steam's code
- ✅ field ContinueInstall: occurs in Steam's code
- ✅ field Downloads: occurs in Steam's code
- ✅ field GamepadUIMainWindowInstance: occurs in Steam's code
- ✅ field GetActiveGameActions: occurs in Steam's code
- ✅ field GetFocusedWindowInstance: occurs in Steam's code
- ✅ field GetLaunchOptionsForApp: occurs in Steam's code
- ✅ field Installs: occurs in Steam's code
- ✅ field LoadEula: occurs in Steam's code
- ✅ field LocalDownloadOverview: occurs in Steam's code
- ✅ field MarkEulaAccepted: occurs in Steam's code
- ✅ field MenuStore: occurs in Steam's code
- ✅ field Navigator: occurs in Steam's code
- ✅ field OpenInstallWizard: occurs in Steam's code
- ✅ field OpenMainMenu: occurs in Steam's code
- ✅ field OpenUninstallWizard: occurs in Steam's code
- ✅ field RegisterForShowInstallWizard: occurs in Steam's code
- ✅ field RunGame: occurs in Steam's code
- ✅ field SetInstallFolder: occurs in Steam's code
- ✅ field SetShortcutName: occurs in Steam's code
- ✅ field Settings: occurs in Steam's code
- ✅ field SteamClient: occurs in Steam's code
- ✅ field SteamUIStore: occurs in Steam's code
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
- ✅ field strNumDone: occurs in Steam's code
- ✅ field strNumTotal: occurs in Steam's code
- ✅ field strSteamID: occurs in Steam's code
- ✅ field strTaskDetails: occurs in Steam's code
- ✅ field strTaskName: occurs in Steam's code
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
| `Apps.AddShortcut` | 1 | 4 | `(pe.strAppName,pe.strExePath,pe.strArguments,pe.strCmdline)` |
| `Apps.BackupFilesForApp` | 1 | 2 | `(O,this.state.strFolder)` |
| `Apps.BrowseScreenshotForApp` | 1 | 2 | `(v.strGameID,v.hHandle)` |
| `Apps.CancelBackup` | 1 | 0 | `()` |
| `Apps.CancelGameAction` | 6 | 1 | `(this.m_nGameActionID)` · `(U)` |
| `Apps.CancelLaunch` | 1 | 1 | `(kt.GetGameID())` |
| `Apps.ClearCustomArtworkForApp` | 2 | 2 | `(this.props.app.appid,this.props.eAssetType)` · `(this.props.overview.appid,Xe)` |
| `Apps.ClearCustomLogoPositionForApp` | 1 | 1 | `(A.appid)` |
| `Apps.ClearProton` | 1 | 1 | `(w)` |
| `Apps.ContinueGameAction` | 6 | 2 | `(this.m_nGameActionID,ze)` · `( "+this.m_nGameActionID+", '"+Ue+"' )` |
| `Apps.CreateDesktopShortcutForApp` | 2 | 1 | `(qt)` · `(kt.appid)` |
| `Apps.DownloadWorkshopItem` | 1 | 3 | `(Y,J,!0)` |
| `Apps.GetAchievementsInTimeRange` | 1 | 3 | `(E,v,B)` |
| `Apps.GetActiveGameActions` | 1 | 0 | `()` |
| `Apps.GetBackupsInFolder` | 1 | 1 | `(b)` |
| `Apps.GetCachedAppDetails` | 1 | 1 | `(l)` |
| `Apps.GetCloudPendingRemoteOperations` | 1 | 1 | `(A.appid)` |
| `Apps.GetConflictingFileTimestamps` | 1 | 1 | `(A.appid)` |
| `Apps.GetDetailsForScreenshotUpload` | 2 | 2 | `(we.strGameID,we.local?.hHandle)` · `(A.strGameID,A.hHandle)` |
| `Apps.GetDetailsForScreenshotUploads` | 1 | 2 | `(tt,Ae[tt])` |
| `Apps.GetDownloadedWorkshopItems` | 1 | 1 | `(Y)` |
| `Apps.GetDurationControlInfo` | 1 | 1 | `(this.appid)` |
| `Apps.GetFriendAchievementsForApp` | 1 | 2 | `(A.toString(),H.ConvertTo64BitString())` |
| `Apps.GetGameActionDetails` | 8 | 2 | `(_e,mt=>Re(mt.nLaunchOption))` · `(this.m_nGameActionID,this.OnGetGameActionDetails)` |
| `Apps.GetGameActionForApp` | 1 | 2 | `(this.props.overview.GetGameID(),this.onGameActionStart)` |
| `Apps.GetIsSubscribedApp` | 2 | 1 | `(this.props.unAppID)` · `(this.props.group.id)` |
| `Apps.GetLaunchOptionsForApp` | 9 | 1 | `(Ve)` · `(xe.appid)` |
| `Apps.GetMyAchievementsForApp` | 1 | 1 | `(A.toString())` |
| `Apps.GetPlaytime` | 1 | 1 | `(this.appid)` |
| `Apps.GetPrePurchasedApps` | 1 | 1 | `(v)` |
| `Apps.GetScreenshotsInTimeRange` | 2 | 3 | `(E.m_unAppID,v,0)` · `(I,0,0)` |
| `Apps.GetShortcutDataForPath` | 1 | 1 | `(X)` |
| `Apps.GetSoundtrackDetails` | 2 | 1 | `(p)` · `(V.appid)` |
| `Apps.GetSubscribedWorkshopItemDetails` | 1 | 2 | `(Y,R)` |
| `Apps.GetSubscribedWorkshopItems` | 2 | 1 | `(Y)` |
| `Apps.InstallFlatpakAppAndCreateShortcut` | 1 | 2 | `(Qe,It)` |
| `Apps.JoinAppContentBeta` | 2 | 2 | `(Vr.unAppID,ci)` · `(Vr.unAppID,Zt.strName)` |
| `Apps.JoinAppContentBetaByPassword` | 1 | 2 | `(Sr,Vr)` |
| `Apps.LaunchNonSteamApp` | 1 | 1 | `(gt.strCmdline)` |
| `Apps.ListFlatpakApps` | 2 | 0 | `()` |
| `Apps.LoadEula` | 1 | 1 | `(this.m_AppID)` |
| `Apps.MarkEulaAccepted` | 2 | 3 | `(le,Ee,Xe)` · `(Z,he,ae)` |
| `Apps.MoveWorkshopItemLoadOrder` | 1 | 3 | `(Y,J,G)` |
| `Apps.OpenAppSettingsDialog` | 3 | 2 | `(kt.appid,"")` · `(this.props.app.appid,"updates")` |
| `Apps.RaiseWindowForGame` | 3 | 1 | `(ge)` · `(this.m_gameid)` |
| `Apps.RegisterForAchievementChanges` | 1 | 1 | `(this.OnAchievementChange)` |
| `Apps.RegisterForAppBackupStatus` | 1 | 1 | `(this.OnAppBackupStatus)` |
| `Apps.RegisterForAppDetails` | 1 | 2 | `(A,this.AppDetailsChanged)` |
| `Apps.RegisterForAppOverviewChanges` | 1 | 1 | `(pe=>{this.UpdateAppOverview(pe)&&(this.m_bIsInitialized=!0,$&&$(),$=null)})` |
| `Apps.RegisterForDRMFailureResponse` | 2 | 1 | `(N)` · `(y)` |
| `Apps.RegisterForGameActionEnd` | 2 | 1 | `(this.OnGameActionEnd)` · `(this.onGameActionEnd)` |
| `Apps.RegisterForGameActionShowError` | 1 | 1 | `(this.OnGameActionShowError)` |
| `Apps.RegisterForGameActionShowUI` | 1 | 1 | `(this.OnGameActionShowUI)` |
| `Apps.RegisterForGameActionStart` | 2 | 1 | `(this.OnGameActionStart)` · `(this.onGameActionStart)` |
| `Apps.RegisterForGameActionTaskChange` | 1 | 1 | `(this.OnGameActionTaskChange)` |
| `Apps.RegisterForGameActionUserRequest` | 1 | 1 | `(this.OnGameActionUserRequest)` |
| `Apps.RegisterForPrePurchasedAppChanges` | 1 | 1 | `(()=>this.ScheduleUpdate(0))` |
| `Apps.RegisterForShowMarketingMessageDialog` | 1 | 1 | `(Qt)` |
| `Apps.RegisterForShowPendingGiftsDialog` | 1 | 1 | `(Qt)` |
| `Apps.RegisterForWorkshopChanges` | 1 | 1 | `(this.onWorkshopChanges)` |
| `Apps.RegisterForWorkshopItemDownloads` | 1 | 2 | `(Y,this.onWorkshopDownload)` |
| `Apps.RegisterForWorkshopItemInstalled` | 1 | 1 | `(this.onWorkshopItemInstalled)` |
| `Apps.RemoveShortcut` | 1 | 1 | `(Bt)` |
| `Apps.ReportLibraryAssetCacheMiss` | 4 | 2 | `(k,this.props.eAssetType)` · `(b,u.uGW)` |
| `Apps.ReportMarketingMessageDialogShown` | 1 | 0 | `()` |
| `Apps.ReportPendingGiftsDialogShown` | 1 | 0 | `()` |
| `Apps.RequestIconDataForApp` | 1 | 1 | `(V.appid)` |
| `Apps.RequestLegacyCDKeysForApp` | 1 | 1 | `(N.appid)` |
| `Apps.RunGame` | 2 | 4 | `(H.GetGameID(),"",-1,d.s7X)` · `(Bt.GetGameID(),"",-1,ct)` |
| `Apps.SaveAchievementProgressCache` | 1 | 1 | `(JSON.stringify(this.m_achievementProgress,w))` |
| `Apps.ScanForInstalledNonSteamApps` | 1 | 1 | `(s)` |
| `Apps.SetAppAutoUpdateBehavior` | 2 | 2 | `(Vr.unAppID,ki.data)` · `(Bi.unAppID,us.data)` |
| `Apps.SetAppBackgroundDownloadsBehavior` | 1 | 2 | `(Vr.unAppID,di.data)` |
| `Apps.SetAppCurrentLanguage` | 1 | 2 | `(Vr.unAppID,nn.data)` |
| `Apps.SetAppLaunchOptions` | 1 | 2 | `(Vr.unAppID,nn)` |
| `Apps.SetAppResolutionOverride` | 1 | 2 | `(Vr.unAppID,ni.data)` |
| `Apps.SetCachedAppDetails` | 1 | 2 | `(l,JSON.stringify(Array.from(f)))` |
| `Apps.SetControllerRumbleIntensity` | 1 | 2 | `(Vr.unAppID,an.data)` |
| `Apps.SetCustomArtworkForApp` | 3 | 4 | `(this.props.app.appid,Y,M,this.props.eAssetType)` · `(Qe,vi,fr,It)` |
| `Apps.SetCustomLogoPositionForApp` | 1 | 2 | `(A.appid,JSON.stringify(H))` |
| `Apps.SetDLCEnabled` | 1 | 3 | `(Vr,si.unAppID,nn)` |
| `Apps.SetFDMEnable` | 1 | 2 | `(Vr.unAppID,Nt)` |
| `Apps.SetForceIdentAsSteamDeck` | 1 | 2 | `(Vr.unAppID,ki)` |
| `Apps.SetLocalScreenshotCaption` | 2 | 3 | `(Ne.local.strGameID,Ne.local.hHandle,le\|\|"")` · `(A.strGameID,A.hHandle,M.strCaption)` |
| `Apps.SetLocalScreenshotPrivacy` | 1 | 3 | `(Ne.local.strGameID,Ne.local.hHandle,Ee)` |
| `Apps.SetLocalScreenshotSpoiler` | 2 | 3 | `(Ne.local.strGameID,Ne.local.hHandle,le)` · `(A.strGameID,A.hHandle,M.bSpoiler)` |
| `Apps.SetRPOEnable` | 1 | 2 | `(Vr.unAppID,Nt)` |
| `Apps.SetShortcutExe` | 2 | 2 | `(Vr,(0,N.yd)(di))` · `(Vr,di)` |
| `Apps.SetShortcutIcon` | 1 | 2 | `(Vr,Ji)` |
| `Apps.SetShortcutIsVR` | 1 | 2 | `(Vr,!nn.bShortcutIsVR)` |
| `Apps.SetShortcutLaunchOptions` | 1 | 2 | `(Vr,di)` |
| `Apps.SetShortcutName` | 1 | 2 | `(Vr,di)` |
| `Apps.SetShortcutSortAs` | 1 | 2 | `(V,ee)` |
| `Apps.SetShortcutStartDir` | 2 | 2 | `(Vr,di)` |
| `Apps.SetStreamingClientForApp` | 1 | 2 | `(this.props.overview.appid,Mt.clientid)` |
| `Apps.SetTSOEnable` | 1 | 2 | `(Vr.unAppID,ni.data)` |
| `Apps.SetThirdPartyControllerConfiguration` | 2 | 2 | `(er,Yr?Y.Dt:Y.pg)` · `(Vr.unAppID,an)` |
| `Apps.SetWorkshopItemsDisabledLocally` | 2 | 3 | `(Vr,[Ri],ln)` · `(Vr.unAppID,Lr,!bt)` |
| `Apps.SetWorkshopItemsLoadOrder` | 1 | 2 | `(Y,he)` |
| `Apps.ShowControllerConfigurator` | 12 | 1 | `(x.qho)` · `(l.mZ)` |
| `Apps.ShowStore` | 2 | 1 | `(kt.appid)` · `(Bt.appid)` |
| `Apps.SpecifyCompatExperiment` | 3 | 2 | `(Vr.unAppID,Nt(Er))` · `(Vr.unAppID,"")` |
| `Apps.StreamGame` | 3 | 3 | `(N.g5s,Ei.clientId,-1)` · `(r.g5s,Z,-1)` |
| `Apps.SubscribeWorkshopItem` | 3 | 3 | `(Y,J,!0)` · `(Y,J,!1)` |
| `Apps.TerminateApp` | 6 | 2 | `(fr,!1)` · `(G,!1)` |
| `Apps.ToggleAllowDesktopConfiguration` | 1 | 1 | `(Vr.unAppID)` |
| `Apps.ToggleAppSteamCloudEnabled` | 1 | 1 | `(Vr.unAppID)` |
| `Apps.ToggleAppSteamCloudSyncOnSuspendEnabled` | 1 | 1 | `(Vr.unAppID)` |
| `Apps.ToggleEnableSteamOverlayForApp` | 2 | 1 | `(Vr.unAppID)` · `(nn.unAppID)` |
| `Apps.ToggleOverrideResolutionForInternalDisplay` | 1 | 1 | `(Vr.unAppID)` |
| `Apps.VerifyApp` | 1 | 1 | `(G)` |
| `Auth.ClearCachedSignInPin` | 1 | 0 | `()` |
| `Auth.CurrentUserHasCachedSignInPin` | 1 | 0 | `()` |
| `Auth.GetLocalHostname` | 3 | 0 | `()` |
| `Auth.GetMachineID` | 1 | 0 | `()` |
| `Auth.GetRefreshInfo` | 2 | 0 | `()` |
| `Auth.GetSteamGuardData` | 2 | 1 | `(Ut)` · `(Mr)` |
| `Auth.IsSecureComputer` | 1 | 0 | `()` |
| `Auth.SetCachedSignInPin` | 1 | 1 | `(Rr)` |
| `Auth.SetLoginToken` | 2 | 2 | `(me.strRefreshToken,me.strAccountName)` · `(He.strRefreshToken,He.strAccountName)` |
| `Auth.SetSteamGuardData` | 2 | 2 | `(me.strAccountName,et)` · `(He.strAccountName,Ke)` |
| `Auth.StartSignInFromCache` | 1 | 1 | `(qt)` |
| `Auth.ValidateCachedSignInPin` | 1 | 2 | `(qt.strAccountName,gt)` |
| `Downloads.EnableAllDownloads` | 5 | 2 | `(!1,qt.clientid)` · `(ei,w.hj.CurrentViewingRemoteClientID)` |
| `Downloads.PauseAppUpdate` | 1 | 2 | `(ce,w.hj.CurrentViewingRemoteClientID)` |
| `Downloads.QueueAppUpdate` | 1 | 2 | `(me,w.hj.CurrentViewingRemoteClientID)` |
| `Downloads.RegisterForDownloadItems` | 1 | 1 | `(this.OnDownloadItems)` |
| `Downloads.RegisterForDownloadOverview` | 1 | 1 | `(this.OnDownloadOverview)` |
| `Downloads.RegisterForRemoteClientsConnected` | 1 | 1 | `(this.OnRemoteClientsChanged)` |
| `Downloads.RemoveFromDownloadList` | 2 | 2 | `($e.appid,w.hj.CurrentViewingRemoteClientID)` |
| `Downloads.ResumeAppUpdate` | 3 | 2 | `(kt.appid,qt.clientid)` · `(ye.appid,i.Oy)` |
| `Downloads.SetLaunchOnUpdateComplete` | 1 | 1 | `(Yt.launch_on_completion?E.sc:Yt.appid)` |
| `Downloads.SetQueueIndex` | 1 | 3 | `(ce,ct.destination.index,w.hj.CurrentViewingRemoteClientID)` |
| `Downloads.SuspendDownloadThrottling` | 1 | 2 |  |
| `Downloads.SuspendLanPeerContent` | 1 | 2 | `(!0,w.hj.CurrentViewingRemoteClientID)` |
| `GameSessions.RegisterForAchievementNotification` | 3 | 1 | `(this.OnAchievementNotification)` |
| `GameSessions.RegisterForAppLifetimeNotifications` | 1 | 1 | `(this.OnAppLifetimeNotification)` |
| `GameSessions.RegisterForScreenshotNotification` | 3 | 1 | `(this.OnScreenshotNotification)` |
| `Installs.CancelInstall` | 8 | 0 | `()` |
| `Installs.ContinueInstall` | 4 | 0 | `()` |
| `Installs.OpenInstallBackup` | 1 | 1 | `(this.state.strFolder)` |
| `Installs.OpenInstallWizard` | 4 | 2 | `([Number(_e)],s.Oy)` · `([G],U)` |
| `Installs.OpenUninstallWizard` | 2 | 3 | `([v.unAppID],a.Oy,!0)` · `(C,D,!0)` |
| `Installs.RegisterForShowConfirmUninstall` | 1 | 1 | `(this.OnShowConfirmUninstall)` |
| `Installs.RegisterForShowFailedUninstall` | 1 | 1 | `(this.OnShowFailedUninstall)` |
| `Installs.RegisterForShowInstallWizard` | 1 | 1 | `(this.OnShowInstallWizard)` |
| `Installs.SetCreateShortcuts` | 1 | 2 | `(G,U)` |
| `Installs.SetInstallFolder` | 2 | 1 | `(G)` |
| `Overlay.DestroyGamePadUIDesktopConfiguratorWindow` | 5 | 0 | `()` |
| `Overlay.GetOverlayBrowserInfo` | 1 | 0 | `()` |
| `Overlay.HandleGameWebCallback` | 1 | 1 | `(w)` |
| `Overlay.HandleProtocolForOverlayBrowser` | 1 | 2 | `(this.m_unAppID,w)` |
| `Overlay.RegisterForActivateOverlayRequests` | 1 | 1 | `(this.OnGameOverlayActivateRequested)` |
| `Overlay.RegisterForMicroTxnAuth` | 2 | 1 | `(this.OnMicroTxnAuth)` · `(En)` |
| `Overlay.RegisterForMicroTxnAuthDismiss` | 2 | 1 | `(this.OnMicroTxnAuthDismiss)` · `(Yn)` |
| `Overlay.RegisterForNotificationPositionChanged` | 1 | 1 | `(this.OverlayNotificationPositionChanged)` |
| `Overlay.RegisterForOverlayActivated` | 2 | 1 | `(P)` · `(this.OnOverlayActivated)` |
| `Overlay.RegisterForOverlayBrowserProtocols` | 1 | 1 | `(this.OnOverlayBrowserProtocol)` |
| `Overlay.RegisterOverlayBrowserInfoChanged` | 1 | 1 | `(this.OnOverlayBrowserInfoChanged)` |
| `Overlay.SetOverlayState` | 15 | 2 | `(M.gameid,k)` · `(Nt.gameid,Re.I5.Overlay)` |
| `Overlay.SetWindowAlpha` | 2 | 1 | `(Or)` · `(1)` |
| `Overlay.SetWindowPinned` | 1 | 1 | `(!br)` |
| `Settings.AddClientBeta` | 1 | 2 | `(Ct,be)` |
| `Settings.ClearAllHTTPCaches` | 1 | 0 | `()` |
| `Settings.ClearDownloadCache` | 1 | 0 | `()` |
| `Settings.GetAccountSettings` | 2 | 0 | `()` |
| `Settings.GetAppUsesP2PVoice` | 1 | 1 | `(us??0)` |
| `Settings.GetAvailableLanguages` | 2 | 0 | `()` |
| `Settings.GetAvailableTimeZones` | 2 | 0 | `()` |
| `Settings.GetCurrentLanguage` | 2 | 0 | `()` |
| `Settings.GetMonitorInfo` | 1 | 0 | `()` |
| `Settings.GetRegisteredSteamDeck` | 1 | 0 | `()` |
| `Settings.GetTimeZone` | 1 | 0 | `()` |
| `Settings.GetWindowed` | 1 | 0 | `()` |
| `Settings.IgnoreSteamDeckRewards` | 1 | 0 | `()` |
| `Settings.OpenWindowsMicSettings` | 1 | 0 | `()` |
| `Settings.RegisterForAppsWithAutoUpdateOverrides` | 1 | 1 | `(Ii=>Qr(Ii.map(Bi=>Bi.appid)))` |
| `Settings.RegisterForMicVolumeUpdates` | 1 | 1 | `(Qr)` |
| `Settings.RegisterForSettingsArrayChanges` | 1 | 1 | `(this.OnClientSettingsMsgChange)` |
| `Settings.RegisterForSettingsChanges` | 1 | 1 | `(this.OnClientSettingsChange)` |
| `Settings.RegisterForTimeZoneChange` | 2 | 1 | `(h)` · `(this.OnTimeZoneChange)` |
| `Settings.ReinitMicSettings` | 1 | 0 | `()` |
| `Settings.RenderHotkey` | 1 | 1 | `(re)` |
| `Settings.SelectClientBeta` | 6 | 1 | `(m.nBetaID)` · `(T.nBetaID)` |
| `Settings.SetCurrentLanguage` | 2 | 1 | `(E.strShortName)` · `(Me)` |
| `Settings.SetEnableSoftProcessKill` | 1 | 1 | `(Lt)` |
| `Settings.SetHostname` | 1 | 1 | `(We)` |
| `Settings.SetMicTestMode` | 1 | 1 | `(Pr)` |
| `Settings.SetPreferredMonitor` | 1 | 1 | `(De)` |
| `Settings.SetRegisteredSteamDeck` | 2 | 2 | `(r.iA.steamid,U)` |
| `Settings.SetSaveAccountCredentials` | 1 | 1 | `(!Ii)` |
| `Settings.SetSetting` | 1 | 1 | `(X)` |
| `Settings.SetTimeZone` | 2 | 1 | `(E)` · `(S)` |
| `Settings.SetUseNintendoButtonLayout` | 1 | 2 | `(jr.nControllerIndex,tr)` |
| `Settings.SetUseUniversalFaceButtonGlyphs` | 1 | 2 | `(jr.nControllerIndex,me)` |
| `Settings.SetWindowed` | 1 | 1 | `(De)` |
| `Settings.ToggleSteamInstall` | 1 | 0 | `()` |
| `Storage.DeleteKey` | 2 | 1 | `(w)` · `(r)` |
| `Storage.GetString` | 2 | 1 | `(w)` · `(r)` |
| `Storage.SetString` | 3 | 2 | `(w,g)` · `(r,o)` |
| `System.Audio` | 17 | — |  |
| `System.AudioDevices` | 3 | — |  |
| `System.CopyFile` | 2 | 2 | `(dr,Mr)` · `(se,Oe)` |
| `System.CopyFilesToClipboard` | 4 | 1 | `(yt.filter(Boolean))` · `([xi.strExportPath])` |
| `System.CreateTempPath` | 3 | 1 | `(cr)` · `(B)` |
| `System.Devkit` | 3 | — |  |
| `System.Display` | 9 | — |  |
| `System.DisplayManager` | 8 | — |  |
| `System.Dock` | 3 | — |  |
| `System.FormatStorage` | 1 | 1 | `(ze)` |
| `System.GetOSType` | 2 | 0 | `()` |
| `System.GetSystemInfo` | 2 | 0 | `()` |
| `System.IsDeckFactoryImage` | 1 | 0 | `()` |
| `System.IsSteamInTournamentMode` | 2 | 0 | `()` |
| `System.Network` | 16 | — |  |
| `System.NotifyGameOverlayStateChanged` | 1 | 2 | `(B,E)` |
| `System.OpenFileDialog` | 12 | 1 | `({strTitle:(0,s.we)("#AddNonSteam_PickAppTitle"),rgFilters:C(),strInitialFile:Q})` · `({strTitle:(0,c.we)("#MediaManager_SaveDialogTitle"),bChooseDirectory:!0})` |
| `System.OpenInSystemBrowser` | 3 | 1 | `(I)` · `(dr)` |
| `System.OpenLocalDirectoryInSystemExplorer` | 5 | 1 | `(kt.strShortcutStartDir)` · `(kt.strInstallFolder)` |
| `System.Perf` | 28 | — |  |
| `System.RebootToAlternateSystemPartition` | 2 | 0 | `()` |
| `System.RegisterForAirplaneModeChanges` | 1 | 1 | `(this.OnAirplaneModeChanged)` |
| `System.RegisterForBatteryStateChanges` | 1 | 1 | `(this.OnBatteryStateChanged)` |
| `System.RegisterForFormatStorageProgress` | 1 | 1 | `(this.OnFormatStorageProgress)` |
| `System.RegisterForSettingsChanges` | 1 | 1 | `(this.OnSettingsChanged)` |
| `System.Report` | 3 | — |  |
| `System.RestartPC` | 8 | 0 | `()` |
| `System.SetAirplaneMode` | 1 | 1 | `(k)` |
| `System.ShutdownPC` | 1 | 0 | `()` |
| `System.SteamRuntimeSystemInfo` | 1 | 0 | `()` |
| `System.SuspendPC` | 1 | 0 | `()` |
| `System.UI` | 8 | — |  |
| `System.UpdateSettings` | 17 | 1 | `(A.serializeBase64String())` · `(k.serializeBase64String())` |
| `System.VideoRecordingDriverCheck` | 1 | 0 | `()` |
| `UI.EnsureMainWindowCreated` | 1 | 0 | `()` |
| `UI.ExitBigPictureMode` | 3 | 0 | `()` |
| `UI.GetDesiredSteamUIWindows` | 1 | 0 | `()` |
| `UI.GetOSEndOfLifeInfo` | 1 | 0 | `()` |
| `UI.GetUIMode` | 2 | 0 | `()` |
| `UI.NotifyAppInitialized` | 2 | 0 | `()` |
| `UI.NotifyMainWindowShown` | 1 | 0 | `()` |
| `UI.RegisterDesiredSteamUIWindowsChanged` | 1 | 1 | `(this.OnDesiredSteamUIWindowsChanged)` |
| `UI.RegisterForClientConVar` | 1 | 2 |  |
| `UI.RegisterForErrorCondition` | 1 | 1 | `(this.OnErrorCondition)` |
| `UI.RegisterForKioskModeResetSignal` | 1 | 1 | `(this.OnKioskModeReset)` |
| `UI.RegisterForStartupFinished` | 1 | 1 | `(()=>{Y(),window.clearTimeout(G),U.unregister()})` |
| `UI.RegisterForUIModeChanged` | 3 | 1 | `(K=>{this.EnsureCurrentRouteAllowed()})` · `(this.OnUIModeChanged)` |
| `UI.RegisterMoveGamepadUIMainWindowToPrimaryDisplay` | 1 | 1 | `(this.OnMoveGamepadUIMainWindowToPrimaryDisplay)` |
| `UI.ResetErrorCondition` | 1 | 0 | `()` |
| `UI.SetUIMode` | 4 | 1 | `(a.$l2)` · `(a.ogI)` |
| `User.AuthorizeMicrotxn` | 1 | 1 | `(this.m_gidTransID)` |
| `User.CancelMicrotxn` | 1 | 1 | `(this.m_gidTransID)` |
| `User.CancelShutdown` | 1 | 0 | `()` |
| `User.Connect` | 1 | 0 | `()` |
| `User.ForceShutdown` | 1 | — |  |
| `User.ForgetPassword` | 1 | 1 | `(N)` |
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
| `User.RegisterForShowHardwareSurvey` | 1 | 1 | `(k)` |
| `User.RegisterForShutdownDone` | 1 | 1 | `(this.OnShutdownDone)` |
| `User.RegisterForShutdownFailed` | 1 | 1 | `(this.OnShutdownFailed)` |
| `User.RegisterForShutdownStart` | 1 | 1 | `(this.OnShutdownStart)` |
| `User.RegisterForShutdownState` | 1 | 1 | `(this.OnShutdownState)` |
| `User.RegisterShowSaveHardwareDialog` | 1 | 1 | `(re)` |
| `User.RemoveAllUsers` | 1 | 0 | `()` |
| `User.RemoveUser` | 1 | 1 | `(w)` |
| `User.RequestSupportSystemReport` | 1 | 1 | `(Q)` |
| `User.RestartAsUser` | 2 | 1 | `(N)` · `(S)` |
| `User.RestartToLoginScreen` | 2 | 0 | `()` |
| `User.RestartToUserChooser` | 2 | 0 | `()` |
| `User.ResumeSuspendedGames` | 2 | 1 | `(!1)` · `(!0)` |
| `User.RunSurvey` | 3 | 1 | `(E)` · `(k)` |
| `User.SendSurvey` | 1 | 0 | `()` |
| `User.SetAsyncNotificationEnabled` | 2 | 2 | `(Ve.request.appid,!0)` · `(Ve.request.appid,!1)` |
| `User.SetCheckForUpdatesOnRestart` | 1 | 1 | `(!0)` |
| `User.SetLoginCredentials` | 1 | 3 | `(Bt,$e,Yt)` |
| `User.ShowSaveHardwareDialog` | 2 | 0 | `()` |
| `User.SignOutAndRestart` | 1 | 0 | `()` |
| `User.StartLogin` | 2 | 0 | `()` |
| `User.StartOffline` | 1 | 1 | `(!0)` |
| `User.StartRestart` | 14 | 1 | `(!1)` · `(!0)` |
| `User.StartShutdown` | 8 | 1 | `(!0)` |
| `Window.BringToFront` | 32 | 0, 1 | `()` · `(k)` |
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
| `Window.MoveTo` | 7 | 3 | `(this.state.menuLeft,this.state.menuTop,ee??!0)` · `(0,0,!1)` |
| `Window.MoveToLocation` | 3 | 1, 2, 3 | `(this.KeyboardLocation,this.k_nKeyboardWindowOffset)` · `("upper-left",0,Gt.strMonitorDeviceName)` |
| `Window.PositionWindowRelative` | 5 | 5 | `(A,k.left,k.top,k.width,k.height)` · `(b,O,m,this.state.width,this.state.height)` |
| `Window.ProcessShuttingDown` | 1 | 0 | `()` |
| `Window.ResizeTo` | 12 | 3 | `(1280,Li.innerHeight,!1)` · `(Xs.UIDisplayPrefs.nFriendsListSingleWindowWidthPx,Li.innerHeight,!1)` |
| `Window.RestoreWindowSizeAndPosition` | 1 | 1 | `(cr.strRestoreDetails)` |
| `Window.SetComposition` | 1 | 3 | `(k,A,H)` |
| `Window.SetGamepadUIAutoDisplayScale` | 2 | 1 | `(J)` · `(!0)` |
| `Window.SetGamepadUIManualDisplayScaleFactor` | 3 | 1 | `(ae)` · `(J)` |
| `Window.SetHideOnClose` | 5 | 1 | `(!1)` · `(!!w.bHideOnClose)` |
| `Window.SetKeyFocus` | 4 | 1 | `( true )` · `(!0)` |
| `Window.SetMinSize` | 9 | 2 | `(Ln.KO,Ln.rS)` · `(Ln.Y$,Ln.rS)` |
| `Window.SetModal` | 2 | 1 | `(!0)` · `(!1)` |
| `Window.SetResizeGrip` | 2 | 2 | `(w,j)` · `(0,0)` |
| `Window.SetWindowFlashing` | 1 | 1 | `(Br)` |
| `Window.SetWindowIcon` | 7 | 1 | `("voice")` · `("messages")` |
| `Window.ShowWindow` | 14 | 0 | `()` |
| `Window.ToggleFullScreen` | 3 | 1 | `(!De)` · `(!0)` |
| `Window.ToggleMaximize` | 1 | 0 | `()` |

## Almacenes en `window`

`App`, `BrowserAndBackstackInstances`, `ControllerStore`, `DEBUG_GetDesiredSteamUIWindows`, `DEBUG_SuppressWindowType`, `FocusNavController`, `FocusedAppWindowStore`, `LocalizationManager`, `MainWindowBrowserManager`, `NotificationStore`, `RemotePlayStore_SteamUI`, `ResetNewContentRollup`, `SetHoverPresentation`, `SetVoiceAutoShowVideoStream`, `SetVoiceEchoLocalMic`, `SetVoiceForceConnectingStatus`, `SetVoiceForceReconnectingStatus`, `SetVoiceLogDetails`, `ShowVROverlay`, `SteamUIStore`, `SuspendResumeStore`, `SystemAudioDevicesStore`, `SystemDevkitStore`, `SystemDisplayManagerStore`, `SystemDockStore`, `SystemNetworkStore`, `SystemPerfStore`, `SystemPowerStore`, `SystemReportStore`, `SystemStoragStore`, `UpdateStore`, `VRPathProperties`, `appAchievementProgressCache`, `appActivityStore`, `appDetailsCache`, `appDetailsStore`, `appInfoStore`, `appReviewStore`, `appSpotlightStore`, `appStore`, `badgeStore`, `cloudStorage`, `cloudStorageInternalState`, `cm`, `collectionStore`, `communityStore`, `consoleStore`, `controllerConfiguratorStore`, `downloadsStore`, `dragStore`, `friendStore`, `g_FriendsUIApp`, `g_GRS`, `g_LogManager`, `g_PopupManager`, `g_SubscriptionStore`, `g_WindowFocusCoordinator`, `gameReleaseStore`, `hardwarePromoStore`, `installFolderStore`, `jsonit`, `libraryEventStore`, `loginStore`, `multiSelectStore`, `onYouTubeIframeAPIReady`, `overlayStore`, `partnerEventStore`, `playNextStore`, `protoPathProperties`, `screenshotStore`, `searchstore`, `securitystore`, `serverBrowserStore`, `settingsStore`, `settingsZooStore`, `showcaseStore`, `steamAjaxRequest`, `streamingStore`, `subscriberAgreementStore`, `tempNavStore`, `toJS`, `trendingStore`, `uiBroadcastWatchStore`, `uiStore`, `urlStore`, `userProfileStore`, `vrAudioSettingsStore`, `vrFrameStore`, `vrGamepadInput`, `vrPooledPopupStore`, `workshopStore`

## Enumeraciones que STONE usa

- `k_EInstallMgrState`: one = 0, etup = 1, aitLicense = 2, reeLicense = 3, howCDKey = 4, aitAppInfo = 5, howPassword = 6, howConfig = 7, howEULAs = 8, reateApps = 9, eadFromMedia = 10, howChangeMedia = 11, aitLegacyCDKeys = 12, howSignup = 13, omplete = 14, ailed = 15, anceled = 16
- `k_EAppUpdateProgress`: VerifyingInstalledFiles = 0, Preallocating = 1, Download = 2, Staging = 3, VerifyingStagedFiles = 4, Copying = 5, Committing = 6, Max = 7
- `k_ELaunchOptionType`: None = 0, Default = 1, SafeMode = 2, Multiplayer = 3, Config = 4, OpenVR = 5, Server = 6, Editor = 7, Manual = 8, Benchmark = 9, Option1 = 10, Option2 = 11, Option3 = 12, OculusVR = 13, OpenVROverlay = 14, OSVR = 15, OpenXR = 16
