from backend.platforms.base import BasePlatform
from backend.platforms.weibo import WeiboPlatform
from backend.platforms.wechat import WechatPlatform
from backend.platforms.douyin import DouyinPlatform
from backend.platforms.xiaohongshu import XiaohongshuPlatform
from backend.platforms.bilibili import BilibiliPlatform

PLATFORM_REGISTRY: dict[str, type[BasePlatform]] = {
    "weibo": WeiboPlatform,
    "wechat": WechatPlatform,
    "douyin": DouyinPlatform,
    "xiaohongshu": XiaohongshuPlatform,
    "bilibili": BilibiliPlatform,
}


def get_platform(platform_name: str) -> BasePlatform:
    cls = PLATFORM_REGISTRY.get(platform_name)
    if not cls:
        raise ValueError(f"Unknown platform: {platform_name}")
    return cls()


__all__ = [
    "BasePlatform", "WeiboPlatform", "WechatPlatform",
    "DouyinPlatform", "XiaohongshuPlatform", "BilibiliPlatform",
    "PLATFORM_REGISTRY", "get_platform",
]
