from functools import wraps

import pytest
from wireup import abstract, create_sync_container, injectable, instance
from wireup.errors import WireupError


@pytest.mark.parametrize("factory", [False, True])
@pytest.mark.parametrize(
    ("first", "second"),
    [(None, None), (None, "message"), ("message", None), ("message", "alert"), ("alert", "message")],
)
def test_repeated_injectable_raises_without_overwriting_registration(factory, first, second):
    class MessageSender: ...

    class AlertSender: ...

    class EmailNotifier(MessageSender, AlertSender): ...

    def make_notifier() -> EmailNotifier:
        return EmailNotifier()

    provider = make_notifier if factory else EmailNotifier
    types = {None: None, "message": MessageSender, "alert": AlertSender}
    assert injectable(provider, as_type=types[first]) is provider
    original = provider.__wireup_registration__

    with pytest.raises(WireupError, match="Stacking @injectable or @abstract decorators is not supported"):
        injectable(provider, as_type=types[second])

    assert provider.__wireup_registration__ is original
    container = create_sync_container(injectables=[provider, provider])
    key = types[first] if first is not None else EmailNotifier
    assert isinstance(container.get(key), EmailNotifier)


@pytest.mark.parametrize("options", [{"qualifier": "other"}, {"lifetime": "scoped"}])
def test_changing_qualifier_or_lifetime_does_not_overwrite_registration(options):
    @injectable
    class MessageSender: ...

    with pytest.raises(WireupError, match=r"Cannot register .* more than once"):
        injectable(MessageSender, **options)

    assert isinstance(create_sync_container(injectables=[MessageSender]).get(MessageSender), MessageSender)


def test_stacked_injectable_decorators_raise():
    with pytest.raises(WireupError, match="Stacking"):

        @injectable(qualifier="other")
        @injectable
        class MessageSender: ...


@pytest.mark.filterwarnings("ignore:Deprecated:FutureWarning")
@pytest.mark.parametrize("first", [injectable, abstract])
@pytest.mark.parametrize("second", [injectable, abstract])
def test_duplicate_decorators_raise(first, second):
    class MessageSender: ...

    first(MessageSender)
    original = MessageSender.__wireup_registration__
    with pytest.raises(WireupError, match="more than once"):
        second(MessageSender)
    assert MessageSender.__wireup_registration__ is original


@pytest.mark.filterwarnings("ignore:Deprecated:FutureWarning")
@pytest.mark.parametrize("decorate_parent", [injectable, abstract])
def test_decorating_subclass_does_not_conflict_with_parent(decorate_parent):
    @decorate_parent
    class Parent: ...

    original = Parent.__wireup_registration__

    @injectable
    class Child(Parent): ...

    assert Parent.__wireup_registration__ is original
    assert Child.__wireup_registration__.obj is Child
    assert isinstance(create_sync_container(injectables=[Child]).get(Child), Child)


def test_copied_wrapper_metadata_does_not_conflict_with_original():
    class MessageSender: ...

    @injectable
    def original() -> MessageSender:
        return MessageSender()

    registration = original.__wireup_registration__

    @injectable
    @wraps(original)
    def wrapped() -> MessageSender:
        return original()

    assert original.__wireup_registration__ is registration
    assert wrapped.__wireup_registration__.obj is wrapped
    assert isinstance(create_sync_container(injectables=[wrapped]).get(MessageSender), MessageSender)


def test_instance_registrations_can_share_an_object():
    class MessageSender: ...

    class EmailNotifier(MessageSender): ...

    notifier = EmailNotifier()
    container = create_sync_container(
        injectables=[instance(notifier, as_type=EmailNotifier), instance(notifier, as_type=MessageSender)]
    )
    assert container.get(EmailNotifier) is notifier
    assert container.get(MessageSender) is notifier
