import unittest
import utils
from unittest.mock import MagicMock, patch

class TestCaching(unittest.TestCase):
    def setUp(self):
        # Limpiar cache antes de cada test
        utils.METADATA_CACHE = {}

    @patch('utils.get_robust_session')
    def test_caching_behavior(self, mock_get_session):
        # Configurar mock para devolver una respuesta falsa
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'metas': [{'name': 'Test Movie', 'poster': 'http://poster.jpg', 'runtime': '120 min'}]
        }
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session

        # 1. Primera llamada (debería llamar a la API)
        data1 = utils.obtener_metadatos("Test Movie", "peli")
        self.assertEqual(data1['name'], "Test Movie")
        self.assertTrue(mock_session.get.called)
        
        # Verificar que se guardó en cache
        self.assertIn(("Test Movie", "peli"), utils.METADATA_CACHE)

        # Resetear mock para verificar que NO se llama de nuevo
        mock_session.get.reset_mock()

        # 2. Segunda llamada (debería usar cache)
        data2 = utils.obtener_metadatos("Test Movie", "peli")
        self.assertEqual(data2['name'], "Test Movie")
        self.assertFalse(mock_session.get.called) # NO debería llamarse a get()

if __name__ == '__main__':
    unittest.main()
