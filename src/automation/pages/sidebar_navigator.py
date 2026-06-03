from collections.abc import Awaitable, Callable


class SidebarNavigator:
    """Generic sidebar navigation helper. Caller owns the item list and step reporter."""

    async def navigate(
        self,
        home,
        items: list[tuple[str, str]],
        step_fn: Callable[..., Awaitable[None]],
    ) -> None:
        """Iterate sidebar items, calling step_fn(name, coro?) for each."""
        for step_name, img in items:
            if home:
                await step_fn(step_name, home.click_sidebar_item(img))
            else:
                await step_fn(step_name)
