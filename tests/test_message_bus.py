"""
Tests for the MessageBus inter-agent communication system.
Covers publish/subscribe, broadcast vs directed delivery, filtering,
message log queries, and error handling in handlers.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from family_office.core.message_bus import MessageBus
from family_office.core.models import AgentRole, Message, MessageType


# ═══════════════════════════════════════════════════════════════
# Basic pub/sub
# ═══════════════════════════════════════════════════════════════


class TestSubscribeAndPublish:

    @pytest.mark.asyncio
    async def test_subscribe_type_receives_broadcast(self, message_bus):
        """A type subscriber receives broadcast messages (recipient=None)."""
        handler = AsyncMock()
        message_bus.subscribe_type(MessageType.ALERT, AgentRole.FUNDAMENTAL, handler)

        msg = Message(
            type=MessageType.ALERT,
            sender=AgentRole.RISK_MANAGER,
            payload={"level": "high"},
        )
        await message_bus.publish(msg)

        handler.assert_awaited_once_with(msg)

    @pytest.mark.asyncio
    async def test_subscribe_type_does_not_echo_to_sender(self, message_bus):
        """A subscriber does NOT receive its own broadcast messages."""
        handler = AsyncMock()
        message_bus.subscribe_type(MessageType.ALERT, AgentRole.RISK_MANAGER, handler)

        msg = Message(
            type=MessageType.ALERT,
            sender=AgentRole.RISK_MANAGER,  # same as subscriber
        )
        await message_bus.publish(msg)

        handler.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_directed_message_reaches_only_target(self, message_bus):
        """A directed message only reaches the target subscriber, not others of same type."""
        handler_fundamental = AsyncMock()
        handler_macro = AsyncMock()
        message_bus.subscribe_type(MessageType.ANALYSIS_REQUEST, AgentRole.FUNDAMENTAL, handler_fundamental)
        message_bus.subscribe_type(MessageType.ANALYSIS_REQUEST, AgentRole.MACRO_GEOPOLITICS, handler_macro)

        msg = Message(
            type=MessageType.ANALYSIS_REQUEST,
            sender=AgentRole.CIO,
            recipient=AgentRole.FUNDAMENTAL,
        )
        await message_bus.publish(msg)

        handler_fundamental.assert_awaited_once_with(msg)
        handler_macro.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_subscribe_direct_receives_directed_message(self, message_bus):
        """subscribe_direct handler receives messages directed to that role."""
        handler = AsyncMock()
        message_bus.subscribe_direct(AgentRole.FUNDAMENTAL, handler)

        msg = Message(
            type=MessageType.ANALYSIS_REQUEST,
            sender=AgentRole.CIO,
            recipient=AgentRole.FUNDAMENTAL,
        )
        await message_bus.publish(msg)

        handler.assert_awaited_once_with(msg)

    @pytest.mark.asyncio
    async def test_subscribe_direct_ignores_broadcast(self, message_bus):
        """subscribe_direct handler does NOT receive broadcast messages."""
        handler = AsyncMock()
        message_bus.subscribe_direct(AgentRole.FUNDAMENTAL, handler)

        msg = Message(
            type=MessageType.ALERT,
            sender=AgentRole.RISK_MANAGER,
            # recipient is None (broadcast)
        )
        await message_bus.publish(msg)

        handler.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_subscribe_direct_ignores_messages_to_others(self, message_bus):
        """subscribe_direct handler ignores messages directed to a different role."""
        handler = AsyncMock()
        message_bus.subscribe_direct(AgentRole.FUNDAMENTAL, handler)

        msg = Message(
            type=MessageType.ANALYSIS_REQUEST,
            sender=AgentRole.CIO,
            recipient=AgentRole.MACRO_GEOPOLITICS,
        )
        await message_bus.publish(msg)

        handler.assert_not_awaited()


# ═══════════════════════════════════════════════════════════════
# Multiple subscribers
# ═══════════════════════════════════════════════════════════════


class TestMultipleSubscribers:

    @pytest.mark.asyncio
    async def test_broadcast_reaches_all_type_subscribers(self, message_bus):
        """Broadcast goes to all subscribers of that message type."""
        handlers = [AsyncMock() for _ in range(3)]
        roles = [AgentRole.FUNDAMENTAL, AgentRole.MACRO_GEOPOLITICS, AgentRole.TECHNICAL_QUANT]

        for role, handler in zip(roles, handlers):
            message_bus.subscribe_type(MessageType.DATA_UPDATE, role, handler)

        msg = Message(
            type=MessageType.DATA_UPDATE,
            sender=AgentRole.PORTFOLIO_OPS,
        )
        await message_bus.publish(msg)

        for handler in handlers:
            handler.assert_awaited_once_with(msg)

    @pytest.mark.asyncio
    async def test_multiple_handlers_on_same_role(self, message_bus):
        """Multiple direct handlers for the same role all fire."""
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        message_bus.subscribe_direct(AgentRole.CIO, handler1)
        message_bus.subscribe_direct(AgentRole.CIO, handler2)

        msg = Message(
            type=MessageType.COMMITTEE_DECISION,
            sender=AgentRole.INVESTMENT_COMMITTEE,
            recipient=AgentRole.CIO,
        )
        await message_bus.publish(msg)

        handler1.assert_awaited_once_with(msg)
        handler2.assert_awaited_once_with(msg)

    @pytest.mark.asyncio
    async def test_unrelated_type_not_delivered(self, message_bus):
        """Subscribing to ALERT does not get VETO messages."""
        handler = AsyncMock()
        message_bus.subscribe_type(MessageType.ALERT, AgentRole.CIO, handler)

        msg = Message(type=MessageType.VETO, sender=AgentRole.RISK_MANAGER)
        await message_bus.publish(msg)

        handler.assert_not_awaited()


# ═══════════════════════════════════════════════════════════════
# Error handling
# ═══════════════════════════════════════════════════════════════


class TestErrorHandling:

    @pytest.mark.asyncio
    async def test_handler_exception_does_not_break_delivery(self, message_bus):
        """If one handler raises, other handlers still receive the message."""
        failing_handler = AsyncMock(side_effect=RuntimeError("boom"))
        good_handler = AsyncMock()

        message_bus.subscribe_type(MessageType.ALERT, AgentRole.FUNDAMENTAL, failing_handler)
        message_bus.subscribe_type(MessageType.ALERT, AgentRole.MACRO_GEOPOLITICS, good_handler)

        msg = Message(type=MessageType.ALERT, sender=AgentRole.RISK_MANAGER)
        await message_bus.publish(msg)

        # Both were called, but the failing one threw
        failing_handler.assert_awaited_once()
        good_handler.assert_awaited_once_with(msg)

    @pytest.mark.asyncio
    async def test_message_logged_even_on_handler_error(self, message_bus):
        """Message appears in the log regardless of handler exceptions."""
        failing_handler = AsyncMock(side_effect=ValueError("oops"))
        message_bus.subscribe_type(MessageType.ALERT, AgentRole.CIO, failing_handler)

        msg = Message(type=MessageType.ALERT, sender=AgentRole.RISK_MANAGER)
        await message_bus.publish(msg)

        log = message_bus.get_message_log()
        assert len(log) == 1
        assert log[0].id == msg.id


# ═══════════════════════════════════════════════════════════════
# Message log
# ═══════════════════════════════════════════════════════════════


class TestMessageLog:

    @pytest.mark.asyncio
    async def test_all_published_messages_are_logged(self, message_bus):
        for i in range(5):
            await message_bus.publish(
                Message(type=MessageType.DATA_UPDATE, sender=AgentRole.PORTFOLIO_OPS)
            )
        log = message_bus.get_message_log()
        assert len(log) == 5

    @pytest.mark.asyncio
    async def test_filter_by_type(self, message_bus):
        await message_bus.publish(Message(type=MessageType.ALERT, sender=AgentRole.RISK_MANAGER))
        await message_bus.publish(Message(type=MessageType.VETO, sender=AgentRole.RISK_MANAGER))
        await message_bus.publish(Message(type=MessageType.ALERT, sender=AgentRole.CIO))

        alerts = message_bus.get_message_log(msg_type=MessageType.ALERT)
        assert len(alerts) == 2
        assert all(m.type == MessageType.ALERT for m in alerts)

    @pytest.mark.asyncio
    async def test_filter_by_sender(self, message_bus):
        await message_bus.publish(Message(type=MessageType.ALERT, sender=AgentRole.RISK_MANAGER))
        await message_bus.publish(Message(type=MessageType.ALERT, sender=AgentRole.CIO))

        risk_msgs = message_bus.get_message_log(sender=AgentRole.RISK_MANAGER)
        assert len(risk_msgs) == 1
        assert risk_msgs[0].sender == AgentRole.RISK_MANAGER

    @pytest.mark.asyncio
    async def test_filter_by_correlation_id(self, message_bus):
        await message_bus.publish(
            Message(type=MessageType.ALERT, sender=AgentRole.CIO, correlation_id="abc")
        )
        await message_bus.publish(
            Message(type=MessageType.ALERT, sender=AgentRole.CIO, correlation_id="xyz")
        )
        await message_bus.publish(
            Message(type=MessageType.ALERT, sender=AgentRole.CIO)  # no corr id
        )

        filtered = message_bus.get_message_log(correlation_id="abc")
        assert len(filtered) == 1
        assert filtered[0].correlation_id == "abc"

    @pytest.mark.asyncio
    async def test_filter_combined(self, message_bus):
        await message_bus.publish(
            Message(type=MessageType.VETO, sender=AgentRole.RISK_MANAGER, correlation_id="p1")
        )
        await message_bus.publish(
            Message(type=MessageType.VETO, sender=AgentRole.HEAD_TAX_STRATEGY, correlation_id="p1")
        )
        await message_bus.publish(
            Message(type=MessageType.ALERT, sender=AgentRole.RISK_MANAGER, correlation_id="p1")
        )

        filtered = message_bus.get_message_log(
            msg_type=MessageType.VETO, sender=AgentRole.RISK_MANAGER, correlation_id="p1"
        )
        assert len(filtered) == 1

    @pytest.mark.asyncio
    async def test_log_limit(self, message_bus):
        for _ in range(10):
            await message_bus.publish(
                Message(type=MessageType.DATA_UPDATE, sender=AgentRole.PORTFOLIO_OPS)
            )
        limited = message_bus.get_message_log(limit=3)
        assert len(limited) == 3
        # Should be the LAST 3 messages
        full = message_bus.get_message_log()
        assert limited == full[-3:]

    @pytest.mark.asyncio
    async def test_clear_log(self, message_bus):
        await message_bus.publish(Message(type=MessageType.ALERT, sender=AgentRole.CIO))
        assert len(message_bus.get_message_log()) == 1
        message_bus.clear_log()
        assert len(message_bus.get_message_log()) == 0


# ═══════════════════════════════════════════════════════════════
# Concurrency
# ═══════════════════════════════════════════════════════════════


class TestConcurrency:

    @pytest.mark.asyncio
    async def test_concurrent_publishes(self, message_bus):
        """Multiple concurrent publishes should all be logged without data loss."""
        messages = [
            Message(type=MessageType.DATA_UPDATE, sender=AgentRole.PORTFOLIO_OPS)
            for _ in range(20)
        ]
        await asyncio.gather(*(message_bus.publish(m) for m in messages))
        assert len(message_bus.get_message_log()) == 20
