from src.backend.app.util import context


def test_set_context():
    ctx = context.request_context.get()
    assert ctx
    assert not hasattr(ctx, "foo")
    context.set_context("foo", "bar")
    assert hasattr(ctx, "foo") and ctx.foo == "bar"


def test_get_db():
    ctx = context.request_context.get()
    assert ctx
    assert hasattr(ctx, "db") and ctx.db is None

    assert context.get_db() is None

    ctx.db = "db"
    assert context.get_db() == "db"


def test_get_current_user():
    ctx = context.request_context.get()
    assert ctx
    assert hasattr(ctx, "user") and ctx.user is None

    assert context.get_current_user() is None

    ctx.user = "user"
    assert context.get_current_user() == "user"


def test_get_current_org():
    ctx = context.request_context.get()
    assert ctx
    assert hasattr(ctx, "org") and ctx.org is None

    assert context.get_current_org() is None

    ctx.org = "org"
    assert context.get_current_org() == "org"
