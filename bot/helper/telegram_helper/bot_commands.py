from bot import CMD_SUFFIX


class _BotCommands:
    def __init__(self):
        self.StartCommand = "start"
        self.MirrorCommand = [f"mirror{CMD_SUFFIX}", f"m{CMD_SUFFIX}"]
        self.QbMirrorCommand = [f"qbmirror{CMD_SUFFIX}", f"qm{CMD_SUFFIX}"]
        self.JdMirrorCommand = [f"jdmirror{CMD_SUFFIX}", f"jm{CMD_SUFFIX}"]
        self.YtdlCommand = [f"ytdl{CMD_SUFFIX}", f"y{CMD_SUFFIX}"]
        self.LeechCommand = [f"leech{CMD_SUFFIX}", f"l{CMD_SUFFIX}"]
        self.QbLeechCommand = [f"qbleech{CMD_SUFFIX}", f"ql{CMD_SUFFIX}"]
        self.JdLeechCommand = [f"jdLeech{CMD_SUFFIX}", f"jl{CMD_SUFFIX}"]
        self.YtdlLeechCommand = [f"ytdlleech{CMD_SUFFIX}", f"yl{CMD_SUFFIX}"]
        self.CloneCommand = f"clone{CMD_SUFFIX}"
        self.CountCommand = f"count{CMD_SUFFIX}"
        self.DeleteCommand = f"del{CMD_SUFFIX}"
        self.CancelTaskCommand = f"cancel{CMD_SUFFIX}"
        self.CancelAllCommand = f"cancelall{CMD_SUFFIX}"
        self.ListCommand = f"list{CMD_SUFFIX}"
        self.SearchCommand = f"search{CMD_SUFFIX}"
        self.StatusCommand = f"status{CMD_SUFFIX}"
        self.UsersCommand = f"users{CMD_SUFFIX}"
        self.AuthorizeCommand = f"authorize{CMD_SUFFIX}"
        self.UnAuthorizeCommand = f"unauthorize{CMD_SUFFIX}"
        self.AddSudoCommand = f"addsudo{CMD_SUFFIX}"
        self.RmSudoCommand = f"rmsudo{CMD_SUFFIX}"
        self.PingCommand = f"ping{CMD_SUFFIX}"
        self.RestartCommand = f"restart{CMD_SUFFIX}"
        self.StatsCommand = f"stats{CMD_SUFFIX}"
        self.HelpCommand = f"help{CMD_SUFFIX}"
        self.LogCommand = f"log{CMD_SUFFIX}"
        self.ExecHelpCommand = f"exechelp{CMD_SUFFIX}"
        self.ShellCommand = f"shell{CMD_SUFFIX}"
        self.AExecCommand = f"aexec{CMD_SUFFIX}"
        self.ExecCommand = f"exec{CMD_SUFFIX}"
        self.ClearLocalsCommand = f"clearlocals{CMD_SUFFIX}"
        self.SpeedCommand = f"speedtest{CMD_SUFFIX}"
        self.WayBackCommand = f"wayback{CMD_SUFFIX}"
        self.HashCommand = f"hash{CMD_SUFFIX}"
        self.BypassCommand = f"bypass{CMD_SUFFIX}"
        self.MiscCommand = f"misc{CMD_SUFFIX}"
        self.UserSetCommand = f"uset{CMD_SUFFIX}"
        self.SleepCommand = f"sleep{CMD_SUFFIX}"
        self.BtSelectCommand = f"btsel{CMD_SUFFIX}"
        self.ScrapperCommand = f"scrap{CMD_SUFFIX}"
        self.PurgeCommand = f"purg{CMD_SUFFIX}"
        self.InfoCommand = f"info{CMD_SUFFIX}"
        self.BroadcaseCommand = f"bc{CMD_SUFFIX}"
        self.BotSetCommand = f"bset{CMD_SUFFIX}"
        self.UserSetPremiCommand = f"premi{CMD_SUFFIX}"
        self.DailyResetCommand = f"rdaily{CMD_SUFFIX}"
        self.RssCommand = f"rss{CMD_SUFFIX}"
        self.BackupCommand = f"backup{CMD_SUFFIX}"
        self.JoinChatCommand = f"join{CMD_SUFFIX}"
        self.FastDlCommand = f"fastdl{CMD_SUFFIX}"
        self.LVidCommand = f"vtl{CMD_SUFFIX}"
        self.MVidCommand = f"vtm{CMD_SUFFIX}"
        self.MediaInfoCommand = f"mediainfo{CMD_SUFFIX}"
        self.DdlsCommand = f"ddls{CMD_SUFFIX}"


BotCommands = _BotCommands()
