from config import Settings

PROVIDERS = ["manual", "minimax_api", "hailuo_web", "kenburns", "wan_local"]


def get_provider(name: str, cfg: Settings, log=print, ask=None):
    if name == "kenburns":
        from .kenburns import KenBurnsProvider
        return KenBurnsProvider(log)
    if name == "manual":
        from .manual import ManualProvider
        return ManualProvider(log)
    if name == "minimax_api":
        from .minimax_api import MiniMaxAPIProvider
        return MiniMaxAPIProvider(cfg, log)
    if name == "hailuo_web":
        from .hailuo_web import HailuoWebProvider
        return HailuoWebProvider(cfg, log, ask)
    if name == "wan_local":
        from .wan_local import WanLocalProvider
        return WanLocalProvider(cfg, log)
    raise ValueError(f"provider không hợp lệ: {name}")
