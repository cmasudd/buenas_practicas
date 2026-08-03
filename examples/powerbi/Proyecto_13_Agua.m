let
    FechaInicio = #date(2025, 1, 1),
    FechaFin = Date.From(DateTime.LocalNow()),
    Dispositivos = {75, 94, 113, 216},
    Tablas = List.Transform(
        Dispositivos,
        each fnCargarDispositivoV3(_, FechaInicio, FechaFin)
    ),
    Datos = Table.Combine(Tablas),
    Ordenados = Table.Sort(
        Datos,
        {
            {"fecha", Order.Descending},
            {"codigo_interno", Order.Ascending},
            {"id_sensor", Order.Ascending}
        }
    )
in
    Ordenados
