import unittest

from app import app, socketio
from models import db, User, Message
from tests.test_helpers import (
    cleanup_test_artifacts,
    configure_app_for_tests,
    create_user,
    reset_database,
)


class SocketMessageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configure_app_for_tests()

    @classmethod
    def tearDownClass(cls):
        cleanup_test_artifacts()

    def setUp(self):
        self.ctx = app.app_context()
        self.ctx.push()
        reset_database()
        self.client = app.test_client()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def _socket_client_for(self, user):
        client = socketio.test_client(
            app,
            namespace='/messages',
            auth={'user_id': user.id},
        )

        self.assertTrue(client.is_connected('/messages'))
        return client

    def _event_names(self, client):
        return [event['name'] for event in client.get_received('/messages')]

    def _events(self, client, name):
        return [
            event for event in client.get_received('/messages')
            if event['name'] == name
        ]

    def test_unauthenticated_socket_is_rejected(self):
        client = socketio.test_client(app, namespace='/messages')

        self.assertFalse(client.is_connected('/messages'))

    def test_authenticated_socket_receives_ready_event(self):
        alice = create_user('alice')
        client = self._socket_client_for(alice)

        self.assertIn('messages:ready', self._event_names(client))

    def test_user_can_join_conversation_room(self):
        alice = create_user('alice')
        bob = create_user('bob')

        client = self._socket_client_for(alice)
        client.get_received('/messages')

        client.emit(
            'messages:join',
            {'username': bob.username},
            namespace='/messages',
        )

        events = self._events(client, 'messages:joined')
        self.assertEqual(len(events), 1)

        payload = events[0]['args'][0]
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['partner'], bob.username)

    def test_socket_send_message_creates_database_row_and_broadcasts(self):
        alice = create_user('alice')
        bob = create_user('bob')

        alice_socket = self._socket_client_for(alice)
        bob_socket = self._socket_client_for(bob)

        alice_socket.get_received('/messages')
        bob_socket.get_received('/messages')

        alice_socket.emit(
            'messages:join',
            {'username': bob.username},
            namespace='/messages',
        )
        bob_socket.emit(
            'messages:join',
            {'username': alice.username},
            namespace='/messages',
        )

        alice_joined = self._events(alice_socket, 'messages:joined')
        bob_joined = self._events(bob_socket, 'messages:joined')

        self.assertEqual(len(alice_joined), 1)
        self.assertEqual(len(bob_joined), 1)

        alice_socket.emit(
            'messages:send',
            {
                'username': bob.username,
                'content': 'Hello over WebSocket',
            },
            namespace='/messages',
        )

        alice_events = self._events(alice_socket, 'messages:new')
        bob_events = self._events(bob_socket, 'messages:new')

        self.assertEqual(len(alice_events), 1)
        self.assertEqual(len(bob_events), 1)

        payload = bob_events[0]['args'][0]
        self.assertEqual(payload['content'], 'Hello over WebSocket')
        self.assertEqual(payload['sender'], alice.username)
        self.assertEqual(payload['recipient'], bob.username)

        stored = Message.query.one()
        self.assertEqual(stored.sender_id, alice.id)
        self.assertEqual(stored.recipient_id, bob.id)
        self.assertEqual(stored.content, 'Hello over WebSocket')
        self.assertFalse(stored.read)

    def test_socket_send_rejects_self_message(self):
        alice = create_user('alice')
        client = self._socket_client_for(alice)
        client.get_received('/messages')

        client.emit(
            'messages:send',
            {
                'username': alice.username,
                'content': 'Self message',
            },
            namespace='/messages',
        )

        events = self._events(client, 'messages:error')
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['args'][0]['status'], 'validation_error')


if __name__ == '__main__':
    unittest.main()