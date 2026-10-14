import json
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from lgad_ivcv.gui.matrix_reset import reset_matrix


class MatrixResetTests(unittest.IsolatedAsyncioTestCase):
    async def send_response(self, response):
        socket = AsyncMock()
        socket.recv.return_value = json.dumps(response)
        connection = MagicMock()
        connection.__aenter__ = AsyncMock(return_value=socket)
        connection.__aexit__ = AsyncMock(return_value=False)
        with patch('lgad_ivcv.gui.matrix_reset.websockets.connect', return_value=connection):
            result = await reset_matrix('ws://matrix:8765')
        self.assertEqual(json.loads(socket.send.call_args.args[0]), {'gateway': 'reset'})
        return result

    async def test_verified_restart_succeeds(self):
        response = {'ok': 1, 'event': 'reset', 'restarted': 1}
        self.assertEqual(await self.send_response(response), response)

    async def test_unverified_restart_and_gateway_errors_fail(self):
        for response in ({'ok': 1, 'event': 'reset'}, {'ok': 0, 'error': 'reset failed'}, []):
            with self.subTest(response=response), self.assertRaises(RuntimeError):
                await self.send_response(response)

    async def test_invalid_address_rejected_before_connecting(self):
        with patch('lgad_ivcv.gui.matrix_reset.websockets.connect') as connect:
            with self.assertRaises(ValueError):
                await reset_matrix('localhost:8765')
            connect.assert_not_called()
