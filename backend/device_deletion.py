class DispositivoConMedicionesError(Exception):
    """Impide perder la relación entre un dispositivo y sus mediciones."""


def eliminar_dispositivos_sin_mediciones(cursor, id_list):
    """Elimina dispositivos vacíos y sensores huérfanos sin mediciones."""
    placeholders = ','.join(['%s'] * len(id_list))
    cursor.execute(
        f"SELECT id_dispositivo FROM dispositivos "
        f"WHERE id_dispositivo IN ({placeholders}) FOR UPDATE",
        id_list,
    )
    existing_device_ids = [str(row[0]) for row in cursor.fetchall()]
    if not existing_device_ids:
        return {'devices': 0, 'associations': 0, 'orphan_sensors': 0}

    device_placeholders = ','.join(['%s'] * len(existing_device_ids))
    cursor.execute(
        f"SELECT id_sensor FROM sensores_en_dispositivo "
        f"WHERE id_dispositivo IN ({device_placeholders}) FOR UPDATE",
        existing_device_ids,
    )
    sensor_ids = sorted({str(row[0]) for row in cursor.fetchall()})

    if sensor_ids:
        sensor_placeholders = ','.join(['%s'] * len(sensor_ids))
        cursor.execute(
            f"SELECT id_sensor FROM sensores WHERE id_sensor IN ({sensor_placeholders}) FOR UPDATE",
            sensor_ids,
        )
        cursor.fetchall()
        cursor.execute(
            f"SELECT id_sensor FROM datos WHERE id_sensor IN ({sensor_placeholders}) LIMIT 1",
            sensor_ids,
        )
        if cursor.fetchone() is not None:
            raise DispositivoConMedicionesError()

    cursor.execute(
        f"DELETE FROM sensores_en_dispositivo "
        f"WHERE id_dispositivo IN ({device_placeholders})",
        existing_device_ids,
    )
    associations_deleted = cursor.rowcount

    orphan_sensors_deleted = 0
    if sensor_ids:
        sensor_placeholders = ','.join(['%s'] * len(sensor_ids))
        cursor.execute(
            f"DELETE s FROM sensores AS s "
            f"LEFT JOIN sensores_en_dispositivo AS sed ON sed.id_sensor = s.id_sensor "
            f"LEFT JOIN datos AS d ON d.id_sensor = s.id_sensor "
            f"WHERE s.id_sensor IN ({sensor_placeholders}) "
            f"AND sed.id_sensor IS NULL AND d.id_sensor IS NULL",
            sensor_ids,
        )
        orphan_sensors_deleted = cursor.rowcount

    cursor.execute(
        f"DELETE FROM dispositivos WHERE id_dispositivo IN ({device_placeholders})",
        existing_device_ids,
    )
    return {
        'devices': cursor.rowcount,
        'associations': associations_deleted,
        'orphan_sensors': orphan_sensors_deleted,
    }
