(ProjectId as number, StartDate as date, EndDate as date, PowerBIKey as text) as table =>
let
    // La raíz permanece fija para que Power BI Service reconozca un solo origen.
    ApiBase = "https://api-sensores.cmasccp.cl",
    FechaInicio = Date.ToText(StartDate, "yyyy-MM-dd", "en-US"),
    FechaFin = Date.ToText(EndDate, "yyyy-MM-dd", "en-US"),
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
                        RelativePath =
                            "v3/powerbi/proyectos/"
                            & Text.From(ProjectId)
                            & "/datos",
                        Query = RequestQuery,
                        Headers = [
                            Accept = "application/json",
                            #"X-API-Key" = PowerBIKey
                        ],
                        Timeout = #duration(0, 0, 2, 0),
                        IsRetry = Cursor <> null
                    ]
                )
            ),
            Data = Response[data],
            Rows = try Data[tableData] otherwise {},
            NextCursor = try Data[next_cursor] otherwise null,
            HasMore = try Logical.From(Data[has_more]) otherwise false
        in
            [Rows = Rows, NextCursor = NextCursor, HasMore = HasMore],

    Pages = List.Generate(
        () => GetPage(null),
        each List.Count([Rows]) > 0,
        each if [HasMore] and [NextCursor] <> null
            then Function.InvokeAfter(
                () => GetPage([NextCursor]),
                #duration(0, 0, 0, 1)
            )
            else [Rows = {}, NextCursor = null, HasMore = false],
        each [Rows]
    ),
    Records = List.Combine(Pages),
    BaseColumns = {
        "fecha",
        "fecha_insercion",
        "id_sesion",
        "sesion_descripcion",
        "fecha_inicio",
        "ubicacion",
        "id_proyecto",
        "codigo_interno",
        "dispositivo_descripcion",
        "id_dato_concatenado"
    },
    RawTable = if List.IsEmpty(Records)
        then #table(BaseColumns, {})
        else Table.FromRecords(Records, null, MissingField.UseNull),
    DateColumns = List.Intersect(
        {Table.ColumnNames(RawTable), {"fecha", "fecha_insercion", "fecha_inicio"}}
    ),
    TypedDates = Table.TransformColumns(
        RawTable,
        List.Transform(
            DateColumns,
            (ColumnName) => {
                ColumnName,
                each if _ = null or Text.From(_) = ""
                    then null
                    else DateTime.FromText(Text.From(_), "en-US"),
                type nullable datetime
            }
        )
    ),
    IntegerColumns = List.Intersect(
        {Table.ColumnNames(TypedDates), {"id_sesion", "id_proyecto"}}
    ),
    TypedIds = Table.TransformColumns(
        TypedDates,
        List.Transform(
            IntegerColumns,
            (ColumnName) => {
                ColumnName,
                each if _ = null or Text.From(_) = ""
                    then null
                    else Int64.From(_),
                Int64.Type
            }
        )
    )
in
    TypedIds
