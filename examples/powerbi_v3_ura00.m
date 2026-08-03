let
    // Mantener fija la raíz permite programar la actualización en Power BI Service.
    ApiBase = "https://api-sensores.cmasccp.cl",
    DeviceId = "223",
    FechaInicio = "2026-04-14",
    FechaFin = Date.ToText(Date.From(DateTime.LocalNow()), "yyyy-MM-dd", "en-US"),
    PageSize = "1000",

    GetPage = (Cursor as nullable text) as record =>
        let
            BaseQuery = [
                fecha_inicio = FechaInicio,
                fecha_fin = FechaFin,
                limite = PageSize
            ],
            RequestQuery = if Cursor = null
                then BaseQuery
                else Record.Combine({BaseQuery, [cursor = Cursor]}),
            Response = Json.Document(
                Web.Contents(
                    ApiBase,
                    [
                        RelativePath = "v3/dispositivos/" & DeviceId & "/mediciones",
                        Query = RequestQuery,
                        Headers = [Accept = "application/json"],
                        Timeout = #duration(0, 0, 2, 0)
                    ]
                )
            ),
            Data = Response[data],
            Rows = Data[mediciones],
            NextCursor = try Data[next_cursor] otherwise null,
            HasMore = try Logical.From(Data[has_more]) otherwise false
        in
            [Rows = Rows, NextCursor = NextCursor, HasMore = HasMore],

    Pages = List.Generate(
        () => GetPage(null),
        each List.Count([Rows]) > 0,
        each if [HasMore] and [NextCursor] <> null
            then GetPage([NextCursor])
            else [Rows = {}, NextCursor = null, HasMore = false],
        each [Rows]
    ),
    Records = List.Combine(Pages),
    Schema = type table [
        codigo_interno = nullable text,
        fecha = nullable text,
        fecha_insercion = nullable text,
        id_dato = nullable number,
        id_dispositivo = nullable number,
        id_proyecto = nullable number,
        id_sensor = nullable number,
        id_sesion = nullable number,
        id_variable = nullable number,
        unidad = nullable text,
        valor = nullable text,
        variable_descripcion = nullable text
    ],
    RawTable = Table.FromRecords(Records, Schema, MissingField.UseNull),
    TypedIds = Table.TransformColumnTypes(
        RawTable,
        {
            {"id_dato", Int64.Type},
            {"id_dispositivo", Int64.Type},
            {"id_proyecto", Int64.Type},
            {"id_sensor", Int64.Type},
            {"id_sesion", Int64.Type},
            {"id_variable", Int64.Type}
        }
    ),
    TypedValues = Table.TransformColumns(
        TypedIds,
        {
            {
                "valor",
                each if _ = null or Text.From(_) = ""
                    then null
                    else Number.FromText(Text.From(_), "en-US"),
                type number
            }
        }
    ),
    TypedDates = Table.TransformColumns(
        TypedValues,
        {
            {
                "fecha",
                each if _ = null
                    then null
                    else DateTimeZone.RemoveZone(
                        DateTimeZone.FromText(Text.From(_), "en-US")
                    ),
                type datetime
            },
            {
                "fecha_insercion",
                each if _ = null
                    then null
                    else DateTimeZone.RemoveZone(
                        DateTimeZone.FromText(Text.From(_), "en-US")
                    ),
                type datetime
            }
        }
    )
in
    TypedDates
