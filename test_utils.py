import unittest
import utils

class TestUtils(unittest.TestCase):

    def test_extraer_datos_video_series(self):
        # Casos de series con SxxExx
        self.assertEqual(utils.extraer_datos_video("Breaking Bad S01E01"), ("Breaking Bad", "serie"))
        self.assertEqual(utils.extraer_datos_video("Stranger Things S04E09"), ("Stranger Things", "serie"))
        self.assertEqual(utils.extraer_datos_video("The.Office.US.S03E12.720p"), ("The Office US", "serie"))
        
        # Casos de series con x
        self.assertEqual(utils.extraer_datos_video("Hunter x Hunter 2011 1x01"), ("Hunter x Hunter 2011", "serie"))
        
        # Casos de series con Season
        self.assertEqual(utils.extraer_datos_video("Severance Season 1"), ("Severance", "serie"))

    def test_extraer_datos_video_movies(self):
        # Casos de películas con año
        self.assertEqual(utils.extraer_datos_video("Inception 2010"), ("Inception", "peli"))
        self.assertEqual(utils.extraer_datos_video("The Matrix 1999 1080p"), ("The Matrix", "peli"))
        
        # Casos sin año (auto)
        self.assertEqual(utils.extraer_datos_video("Pulp Fiction"), ("Pulp Fiction", "auto"))

    def test_limpiar_titulo_api(self):
        # Casos de títulos dobles
        self.assertEqual(utils.limpiar_titulo_api("Dungeon Meshi: Delicious in Dungeon", "Dungeon Meshi"), "Dungeon Meshi")
        self.assertEqual(utils.limpiar_titulo_api("Shingeki no Kyojin: Attack on Titan", "Attack on Titan"), "Attack on Titan")
        
        # Casos donde no hay coincidencia clara pero es largo
        long_title = "This Is A Very Long Title That Should Be Split: Subtitle"
        self.assertEqual(utils.limpiar_titulo_api(long_title, "Short"), "This Is A Very Long Title That Should Be Split")
        
        # Casos simples
        self.assertEqual(utils.limpiar_titulo_api("Simple Title", "Simple Title"), "Simple Title")

if __name__ == '__main__':
    unittest.main()
