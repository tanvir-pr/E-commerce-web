"""Redis fixed-window rate limiter for login."""

from redis.asyncio import Redis

from app.problems import PROBLEM_RATE_LIMIT, ProblemError


class RedisRateLimiter:
    def __init__(self, redis: Redis, *, limit: int, window_seconds: int, prefix: str) -> None:
        self.redis = redis
        self.limit = limit
        self.window_seconds = window_seconds
        self.prefix = prefix

    async def check(self, key: str) -> None:
        redis_key = f"{self.prefix}:{key}"
        count = await self.redis.incr(redis_key)
        if count == 1:
            await self.redis.expire(redis_key, self.window_seconds)
        if count > self.limit:
            raise ProblemError(
                429,
                "Too Many Requests",
                "Too many attempts. Try again later.",
                PROBLEM_RATE_LIMIT,
            )
