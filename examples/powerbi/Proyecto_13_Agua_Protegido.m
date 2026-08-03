let
    FechaInicio = #date(2025, 1, 1),
    FechaFin = Date.From(DateTime.LocalNow()),
    Datos = fnCargarProyectoPowerBIV3(
        13,
        FechaInicio,
        FechaFin,
        PowerBIKey
    ),
    Ordenados = Table.Sort(
        Datos,
        {
            {"fecha", Order.Descending},
            {"codigo_interno", Order.Ascending}
        }
    )
in
    Ordenados
