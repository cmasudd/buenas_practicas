import unittest

from backend.device_deletion import (
    DispositivoConMedicionesError,
    eliminar_dispositivos_sin_mediciones,
)


class FakeCursor:
    def __init__(self, devices=(), sensors=(), measurement=None):
        self.devices = list(devices)
        self.sensors = list(sensors)
        self.measurement = measurement
        self.last_query = ''
        self.queries = []
        self.rowcount = 0

    def execute(self, query, params):
        self.last_query = ' '.join(query.split())
        self.queries.append((self.last_query, list(params)))
        if self.last_query.startswith('DELETE FROM sensores_en_dispositivo'):
            self.rowcount = len(self.sensors)
        elif self.last_query.startswith('DELETE s FROM sensores'):
            self.rowcount = len(self.sensors)
        elif self.last_query.startswith('DELETE FROM dispositivos'):
            self.rowcount = len(self.devices)

    def fetchall(self):
        if self.last_query.startswith('SELECT id_dispositivo'):
            return [(item,) for item in self.devices]
        if self.last_query.startswith('SELECT id_sensor FROM sensores_en_dispositivo'):
            return [(item,) for item in self.sensors]
        if self.last_query.startswith('SELECT id_sensor FROM sensores'):
            return [(item,) for item in self.sensors]
        return []

    def fetchone(self):
        if self.last_query.startswith('SELECT id_sensor FROM datos'):
            return None if self.measurement is None else (self.measurement,)
        return None


class DeviceDeletionTests(unittest.TestCase):
    def test_missing_device_changes_nothing(self):
        cursor = FakeCursor()
        result = eliminar_dispositivos_sin_mediciones(cursor, ['999'])
        self.assertEqual(result, {'devices': 0, 'associations': 0, 'orphan_sensors': 0})
        self.assertFalse(any(query.startswith('DELETE') for query, _ in cursor.queries))

    def test_deletes_empty_device(self):
        result = eliminar_dispositivos_sin_mediciones(FakeCursor(devices=[10]), ['10'])
        self.assertEqual(result['devices'], 1)

    def test_deletes_associations_and_orphans_first(self):
        cursor = FakeCursor(devices=[10], sensors=[101, 102])
        result = eliminar_dispositivos_sin_mediciones(cursor, ['10'])
        self.assertEqual(result, {'devices': 1, 'associations': 2, 'orphan_sensors': 2})
        deletes = [query for query, _ in cursor.queries if query.startswith('DELETE')]
        self.assertIn('sensores_en_dispositivo', deletes[0])
        self.assertIn('dispositivos', deletes[-1])

    def test_rejects_historical_device_before_any_delete(self):
        cursor = FakeCursor(devices=[10], sensors=[101], measurement=101)
        with self.assertRaises(DispositivoConMedicionesError):
            eliminar_dispositivos_sin_mediciones(cursor, ['10'])
        self.assertFalse(any(query.startswith('DELETE') for query, _ in cursor.queries))


if __name__ == '__main__':
    unittest.main()
