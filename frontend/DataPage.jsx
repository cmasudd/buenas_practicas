import { useMsal } from '@azure/msal-react';
import { useState, useEffect } from 'react';
import Select from 'react-select';
import { useFetch } from '../hooks/useFetch';
import { BasicDataTableGraphic } from '../components/graphics/BasicDataTableGraphic';
import { Spinner } from '../components/Spinner';
import { ChartComponent } from '../components/graphics/ChartComponent';
import noVariables from '../helpers/noVariables.json';
import AlertsCreator from '../components/AlertsCreator';
import Otro from '../Otro';
import AlertsList from '../components/AlertsList';
import * as config from '../helpers/config';

// 2025-06-23T21:33:25



export const DataPage = () => {
  // login
  const { accounts, instance } = useMsal();
  const username = accounts.length > 0;
  const visitorLoggedIn = localStorage.getItem("visitorLoggedIn") === "true";

  // Nombre de las tablas
  const projectsTableName = "proyectos";
  const devicesTableName = "dispositivos";
  const [descripcion, setDescripcion] = useState("");

  // Opciones de filtros
  const [projectOptions, setProjectOptions] = useState([]);
  const [deviceOptions, setDeviceOptions] = useState([]);

  // filtros seleccionados
  const [selectedProjects, setSelectedProjects] = useState([]); // Array para selección múltiple
  const [selectedDevices, setSelectedDevices] = useState([]); // Array para selección múltiple
  const [startDate, setStartDate] = useState(''); // Fecha de inicio
  const [endDate, setEndDate] = useState(''); // Fecha de fin
  const [availabilityMonth, setAvailabilityMonth] = useState('');
  const [availabilityYear, setAvailabilityYear] = useState(
    new Date().toLocaleDateString('en-CA').slice(0, 4)
  );

  // Graficos
  const [showChart, setShowChart] = useState(false);
  const [showAlerts, setShowAlerts] = useState(false);
  // Datos de la tabla
  const [tableData, setTableData] = useState([]);
  // datos del gráfico
  const [chartData, setChartData] = useState([]);

  const [isLoading, setIsLoading] = useState(false);


  // Paginación
  const [currentPage, setCurrentPage] = useState(1); // Página actual
  const rowsPerPage = 25; // Número máximo de filas por página
  const [cursorStack, setCursorStack] = useState([null]);
  const [nextCursor, setNextCursor] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [sortOrder, setSortOrder] = useState("desc")

  // Hooks para obtener datos de las tablas
  const { data: projectsData, isLoading: isLoadingProjects } = useFetch(`${import.meta.env.VITE_API_URL}/listarDatos?tabla=${projectsTableName}`);
  const { data: devicesData, setUrl: devicesSetUrl, isLoading: isLoadingDevices } = useFetch('');
  const {
    data: sensorsData,
    setUrl: sensorsSetUrl,
    isLoading: isLoadingSensors,
    forceFetch: forceSensorsFetch,
  } = useFetch('');
  const {
    data: availabilityData,
    setUrl: availabilitySetUrl,
    isLoading: isLoadingAvailability,
  } = useFetch('');
  const {
    data: availableMonthsData,
    setUrl: availableMonthsSetUrl,
    isLoading: isLoadingAvailableMonths,
  } = useFetch('');

  // actualizacion de datos
  const [refreshCount, setRefreshCount] = useState(0);


  // Establece opciones de proyectos
  useEffect(() => {

    setIsLoading(true);
    if (projectsData && projectsData.status === 'success') {
      const options = projectsData.data.tableData.map((project) => ({
        value: project.id_proyecto,
        label: `${project.id_proyecto}. ${project.nombre}`,
      }));
      setProjectOptions(options);
      setIsLoading(false);
    }
  }, [projectsData]);

  // Establece opciones de dispositivos
  useEffect(() => {
    setIsLoading(true);
    if (devicesData && devicesData.status === 'success') {
      const options = devicesData.data.tableData.map((device) => ({
        value: device.id_dispositivo,
        label: device.codigo_interno,
      }));

      setDeviceOptions(options);
      setIsLoading(false);
    }
  }, [devicesData]);

  useEffect(() => {
    if (selectedDevices.length === 0 || !availabilityMonth) {
      availabilitySetUrl('');
      return;
    }
    const params = new URLSearchParams({
      id_dispositivo: selectedDevices.map((device) => device.value).join(','),
      mes: availabilityMonth,
    });
    availabilitySetUrl(
      `${import.meta.env.VITE_API_URL}/v3/disponibilidad?${params.toString()}`
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDevices, availabilityMonth]);

  useEffect(() => {
    if (selectedDevices.length === 0 || !/^\d{4}$/.test(availabilityYear)) {
      availableMonthsSetUrl('');
      return;
    }
    const params = new URLSearchParams({
      id_dispositivo: selectedDevices.map((device) => device.value).join(','),
      anio: availabilityYear,
    });
    availableMonthsSetUrl(
      `${import.meta.env.VITE_API_URL}/v3/disponibilidad-meses?${params.toString()}`
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDevices, availabilityYear]);
  useEffect(() => {
    const refreshTimer = window.setTimeout(refleshTableData, 500);
    const desc = projectsData?.data?.tableData?.filter(proj => proj?.id_proyecto === selectedProjects[0]?.value);
    const handleSetDesc = () => {
      if (desc && desc.length > 0) {
        setDescripcion(desc[0]?.descripcion || "");
      }
    }
    handleSetDesc();
    // console.log(projectsData.data.tableData);
    // console.log(selectedProjects[0]?.value);

    return () => window.clearTimeout(refreshTimer);
  }, [selectedProjects, selectedDevices, startDate, endDate, currentPage, refreshCount]);
  const handleRefresh = () => {
    setCursorStack([null]);
    if (currentPage === 1) {
      forceSensorsFetch();
    } else {
      setCurrentPage(1);
    }
  };
  // Actualiza la peticion de datos dependiendo de dispositivos y proyectos seleccionados
  const refleshTableData = async () => {
    console.log("actualizando datos")
    if (selectedProjects.length > 0) {
      const projectIds = selectedProjects.map((project) => project.value).join(',');
      const deviceCodes = selectedDevices.map((device) => device.label).join(',');
      const deviceIds = selectedDevices.map((device) => device.value).join(',');
      console.log('refleshTableData filters:', { projectIds, deviceIds, startDate, endDate, currentPage, refreshCount });
      setIsLoading(true);
      devicesSetUrl(`${import.meta.env.VITE_API_URL}/listarDatos?tabla=${devicesTableName}&id_proyecto=${projectIds}`);

      if (selectedDevices.length > 0) {
        const previewParams = new URLSearchParams({
          id_dispositivo: deviceIds,
          limite: String(rowsPerPage),
        });
        if (startDate) previewParams.set('fecha_inicio', startDate);
        if (endDate) previewParams.set('fecha_fin', endDate);
        const currentCursor = cursorStack[currentPage - 1];
        if (currentCursor) previewParams.set('cursor', currentCursor);
        const previewUrl = `${import.meta.env.VITE_API_URL}/v3/vista-previa?${previewParams.toString()}`;
        console.log('refleshTableData preview:', { previewUrl, deviceCodes });
        sensorsSetUrl(previewUrl);
        setIsLoading(false);
      } else {
        sensorsSetUrl("");
        setIsLoading(false);
      }
    }
  }


  // Procesa datos de sensores
  useEffect(() => {
    console.log('sensorsData', sensorsData);
    if (sensorsData && sensorsData.status === 'success') {
      setTableData(sensorsData.data.tableData);
      setHasMore(Boolean(sensorsData.data.has_more));
      setNextCursor(sensorsData.data.next_cursor || null);
    } else {
      setTableData([]);
      setHasMore(false);
      setNextCursor(null);
    }
  }, [sensorsData]);

  useEffect(() => {
    setChartData([...tableData].reverse());
    console.log('tableData', tableData);
  }, [tableData]);

  const handleProjectChange = (selectedProjects) => {
    setSelectedProjects(selectedProjects || []); // Permite deseleccionar todo
    setSelectedDevices([]); // Restablece los dispositivos seleccionados
    setCurrentPage(1);
    setCursorStack([null]);
    setAvailabilityMonth('');
  };

  const handleDeviceChange = (selectedDevices) => {
    console.log('selectedDevices', selectedDevices);
    setSelectedDevices(selectedDevices || []); // Permite deseleccionar todo
    setCurrentPage(1);
    setCursorStack([null]);
    setAvailabilityMonth('');
  };

  const handleOlderData = () => {
    if (!hasMore || !nextCursor) return;
    setCursorStack((previous) => [
      ...previous.slice(0, currentPage),
      nextCursor,
    ]);
    setCurrentPage((page) => page + 1);
  };

  const handleRecentData = () => {
    if (currentPage <= 1) return;
    setCurrentPage((page) => page - 1);
  };

  const handleStartDateChange = (event) => {
    setStartDate(event.target.value);
    if (event.target.value) {
      setAvailabilityMonth(event.target.value.slice(0, 7));
      setAvailabilityYear(event.target.value.slice(0, 4));
    }
    if (event.target.value && !endDate) {
      setEndDate(new Date().toLocaleDateString('en-CA'));
    }
    setCurrentPage(1); // Resetear a la primera página
    setCursorStack([null]);
  };

  const handleEndDateChange = (event) => {
    setEndDate(event.target.value);
    if (event.target.value) {
      setAvailabilityMonth(event.target.value.slice(0, 7));
      setAvailabilityYear(event.target.value.slice(0, 4));
    }
    setCurrentPage(1); // Resetear a la primera página
    setCursorStack([null]);
  };

  const handleAvailableDayClick = (day) => {
    setStartDate(day);
    setEndDate(day);
    setCurrentPage(1);
    setCursorStack([null]);
  };

  const handleAvailabilityYearChange = (event) => {
    const year = event.target.value;
    setAvailabilityYear(year);
    if (/^\d{4}$/.test(year)) {
      setAvailabilityMonth('');
    }
  };

  const handleAvailableMonthClick = (month) => {
    setAvailabilityMonth(month);
    setAvailabilityYear(month.slice(0, 4));
  };

  const availabilityDays = new Set(
    availabilityData?.status === 'success'
      ? availabilityData.data.days
      : []
  );
  const availableMonths = new Set(
    availableMonthsData?.status === 'success'
      ? availableMonthsData.data.months
      : []
  );
  const monthNames = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre',
  ];
  const [calendarYear, calendarMonth] = availabilityMonth
    ? availabilityMonth.split('-').map(Number)
    : [Number(availabilityYear), 1];
  const calendarDayCount = new Date(calendarYear, calendarMonth, 0).getDate();
  const calendarStartOffset = (
    new Date(calendarYear, calendarMonth - 1, 1).getDay() + 6
  ) % 7;
  const calendarCells = [
    ...Array(calendarStartOffset).fill(null),
    ...Array.from({ length: calendarDayCount }, (_, index) => index + 1),
  ];

  const customStyles = {
    control: (provided, state) => ({
      ...provided,
      borderColor: state.isFocused ? 'black' : 'gray', // Cambia el color del borde
      boxShadow: state.isFocused ? '0 0 0 2px rgba(44, 44, 44, 0.3)' : 'none', // Sombra en focus
      '&:hover': {
        borderColor: 'black', // Color al pasar el mouse
      },
    }),
    option: (provided, state) => ({
      ...provided,
      backgroundColor: state.isSelected
        ? 'rgb(44, 44, 44)' // Color de la opción seleccionada
        : state.isFocused
          ? 'rgba(44, 44, 44, 0.1)' // Color al pasar el mouse sobre una opción
          : 'white',
      color: state.isSelected
        ? 'white'
        : 'black', // Color del texto de las opciones
    }),
    placeholder: (provided) => ({
      ...provided,
      color: 'gray', // Cambia el color del texto del placeholder
    }),
    singleValue: (provided) => ({
      ...provided,
      color: 'black', // Cambia el color del texto seleccionado
    }),
    container: (provided) => ({
      ...provided,
      width: '300px',
      zIndex: 3, // Ensure dropdown is on top
    }),
    menu: (provided) => ({
      ...provided,
      width: '300px',
      zIndex: 5, // Ensure dropdown is on top
    }),
  };


  const downloadFile = async () => {
    try {
      const deviceIds = selectedDevices.map((device) => device.value).join(',');
      if (!deviceIds) {
        alert('Seleccione al menos un dispositivo para descargar.');
        return;
      }

      if (startDate && endDate && startDate > endDate) {
        alert('La fecha de inicio no puede ser posterior a la fecha de fin.');
        return;
      }

      let authStatus = await fetch(`${import.meta.env.VITE_API_URL}/v3/auth/status`, {
        credentials: 'include',
      });
      if (!authStatus.ok && accounts.length > 0) {
        const tokenResult = await instance.acquireTokenSilent({
          scopes: config.scopeBase,
          account: accounts[0],
        });
        authStatus = await fetch(`${import.meta.env.VITE_API_URL}/v3/auth/microsoft`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id_token: tokenResult.idToken }),
        });
      }
      if (!authStatus.ok) {
        alert('Su sesión no permite descargar. Cierre sesión y vuelva a ingresar.');
        return;
      }

      let url = `${import.meta.env.VITE_API_URL}/v3/historicos.csv?id_dispositivo=${deviceIds}`;

      // Añadir los filtros de fechas si se han especificado
      if (startDate) url += `&fecha_inicio=${startDate}`;
      if (endDate) url += `&fecha_fin=${endDate}`;
      const link = document.createElement('a');
      link.href = url;
      link.download = '';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Error al descargar el archivo:', error);
      alert('No fue posible iniciar la descarga. Actualice la página e intente nuevamente.');
    }
  };
  const downloadExcel = async () => {
    alert('Durante esta prueba la descarga histórica segura está disponible en CSV.');
  };

  const handleDelete = async (rows) => {

    const confirmed = window.confirm("¿Estás seguro que quieres eliminar este registro?");
    if (!confirmed) return;

    console.log(rows)
    let id_datos_sin_espacios = rows.replace(/\s+/g, ''); // Esto elimina todos los espacios en la cadena
    console.log(id_datos_sin_espacios);

    // TODO: que pasaria si selecciona varios proyectos?
    // validar que solo pueda eliminar multiples en solo un proyecto
    console.log(`/eliminarDatos?tabla=datos&id_dato=${id_datos_sin_espacios}`);

    try {
      setIsLoading(true);
      const response = await fetch(`${import.meta.env.VITE_API_URL}/eliminarDatos?tabla=datos&id_dato=${id_datos_sin_espacios}`, {
        method: 'GET',
      });

      if (response.ok) {
        // Actualizar la tabla después de eliminar
        setIsLoading(false);
        alert("Datos eliminados correctamente");
        window.location.reload(); // Recargar la página para actualizar los datos
        console.log("Datos eliminados correctamente");

      } else {
        setIsLoading(false);
        throw new Error('Error al eliminar los datos');
      }
    } catch (error) {
      setIsLoading(false);
      alert("Error al eliminar los datos");
      console.error('Error al eliminar los datos:', error);
    }
  }

  return (
    <>
      {isLoading || isLoadingProjects || isLoadingDevices || isLoadingSensors && (
        <Spinner />
      )}


      <div className="container-fluid d-flex justify-content-center align-items-center">
        <div className="card w-100">
          <h2 className="card-title">Datos</h2>
          <div className="card-content mt-2">
            {(visitorLoggedIn || username) && (
              <div>
                <p>Utilice esta página para visualizar y descargar sus datos.</p>
                <div className="row d-flex justify-content-around my-2 py-4">
                  <div className="col-3">
                    <label htmlFor="start-date">Fecha de inicio</label>
                    <input
                      type="date"
                      id="start-date"
                      value={startDate}
                      onChange={handleStartDateChange}
                      className="form-control"
                    />
                  </div>
                  <div className="col-3">
                    <label htmlFor="end-date">Fecha de fin</label>
                    <input
                      type="date"
                      id="end-date"
                      value={endDate}
                      onChange={handleEndDateChange}
                      className="form-control"
                    />
                  </div>
                </div>
                {selectedDevices.length > 0 && (
                  <div className="mb-4 px-3">
                    <div className="d-flex justify-content-center align-items-end mb-3">
                      <div>
                        <label htmlFor="availability-year">
                          Meses que contienen datos
                        </label>
                        <input
                          type="number"
                          id="availability-year"
                          min="1970"
                          max="2100"
                          value={availabilityYear}
                          onChange={handleAvailabilityYearChange}
                          className="form-control mt-1"
                        />
                      </div>
                    </div>
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(4, minmax(80px, 1fr))',
                        gap: '0.35rem',
                        maxWidth: '640px',
                        margin: '0 auto 0.75rem',
                      }}
                    >
                      {monthNames.map((monthName, index) => {
                        const monthValue = `${availabilityYear}-${String(index + 1).padStart(2, '0')}`;
                        const hasData = availableMonths.has(monthValue);
                        const isSelected = availabilityMonth === monthValue;
                        return (
                          <button
                            type="button"
                            key={monthValue}
                            disabled={!hasData}
                            onClick={() => handleAvailableMonthClick(monthValue)}
                            className={`btn btn-sm ${
                              isSelected && hasData
                                ? 'btn-dark'
                                : hasData
                                  ? 'btn-success'
                                  : 'btn-light text-muted'
                            }`}
                            title={hasData ? 'Este mes contiene datos' : 'Sin datos'}
                          >
                            {monthName}
                          </button>
                        );
                      })}
                    </div>
                    <p className="text-muted text-center mt-2">
                      {isLoadingAvailableMonths
                        ? 'Buscando meses con datos…'
                        : availableMonths.size > 0
                          ? availabilityMonth
                            ? 'Los meses verdes contienen datos.'
                            : 'Seleccione un mes verde para ver sus días.'
                          : 'No se encontraron datos para este año.'}
                    </p>
                    {availabilityMonth && (
                      <>
                        <h6 className="text-center mb-2">
                          Días con datos de {monthNames[calendarMonth - 1]} {calendarYear}
                        </h6>
                        <div
                          style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(7, minmax(36px, 1fr))',
                            gap: '0.25rem',
                            maxWidth: '560px',
                            margin: '0 auto',
                          }}
                        >
                          {['Lu', 'Ma', 'Mi', 'Ju', 'Vi', 'Sá', 'Do'].map((day) => (
                            <strong className="text-center" key={day}>{day}</strong>
                          ))}
                          {calendarCells.map((day, index) => {
                            if (day === null) {
                              return <span key={`empty-${index}`} />;
                            }
                            const dateValue = `${availabilityMonth}-${String(day).padStart(2, '0')}`;
                            const hasData = availabilityDays.has(dateValue);
                            const isSelected = dateValue === startDate || dateValue === endDate;
                            return (
                              <button
                                type="button"
                                key={dateValue}
                                disabled={!hasData}
                                onClick={() => handleAvailableDayClick(dateValue)}
                                className={`btn btn-sm ${
                                  isSelected
                                    ? 'btn-dark'
                                    : hasData
                                      ? 'btn-success'
                                      : 'btn-light text-muted'
                                }`}
                                title={hasData ? 'Este día contiene datos' : 'Sin datos'}
                              >
                                {day}
                              </button>
                            );
                          })}
                        </div>
                        <p className="text-muted text-center mt-2 mb-0">
                          {isLoadingAvailability
                            ? 'Buscando días con datos…'
                            : availabilityDays.size > 0
                              ? 'Los días verdes contienen datos. Seleccione uno para visualizarlo.'
                              : 'No se encontraron datos para este mes.'}
                        </p>
                      </>
                    )}
                  </div>
                )}
                {selectedDevices.length > 0 && (
                  <p className="text-muted text-center">
                    {startDate || endDate
                      ? 'La tabla muestra el rango seleccionado en páginas de 25 mediciones.'
                      : 'La tabla muestra las mediciones más recientes en páginas de 25.'}
                    {' '}La descarga CSV incluye el rango completo.
                  </p>
                )}
                <div className="row d-flex justify-content-around my-2 py-4">
                  <div className="dropdown mb-4 col-3">
                    <label>Proyectos</label>
                    <Select
                      id="project-select"
                      options={projectOptions}
                      onChange={handleProjectChange}
                      value={selectedProjects}
                      placeholder="Seleccione proyectos"
                      className="mt-2"
                      styles={customStyles}
                      isMulti
                    />
                  </div>
                  <div className="dropdown mb-4 col-3">
                    <label>Dispositivos</label>
                    <Select
                      id="device-select"
                      options={deviceOptions}
                      onChange={handleDeviceChange}
                      value={selectedDevices}
                      placeholder="Seleccione dispositivos"
                      className="mt-2"
                      styles={customStyles}
                      isMulti
                    />
                  </div>
                </div>

                {selectedDevices.length > 0 && (
                  <div className="row d-flex justify-content-center my-2">
                    <button className="btn m-1 custom-button" onClick={downloadFile}>
                      <span className="btn-text">Descargar CSV histórico</span>
                      <i className="fas fa-download ms-2" aria-hidden="true"></i>
                    </button>
                    <button className="btn m-1 custom-button" onClick={downloadExcel}>
                      <span className="btn-text">Descargar Excel</span>
                      <i className="fas fa-download ms-2" aria-hidden="true"></i>
                    </button>
                  </div>
                )}

                <div className='row d-flex justify-content-around my-2'>
                  {selectedProjects.length > 0 && tableData.length > 0 && (
                    <>
                      <blockquote>{descripcion}</blockquote>

                      <div className='row'>
                        <button className="btn m-1 ml-auto custom-button" onClick={() => setShowChart(!showChart)}>
                          <span className="btn-text">{showChart ? "Ocultar" : "Mostrar"} gráfico</span>
                          <i className="fas fa-eye me-2" aria-hidden="true"></i>
                        </button>
                        <button className="btn m-1 ml-auto custom-button" onClick={() => setShowAlerts(!showAlerts)}>
                          <span className="btn-text">{showAlerts ? "Ocultar" : "Mostrar"} Alertas</span>
                          <i className="fas fa-eye me-2" aria-hidden="true"></i>
                        </button>
                        <button className="btn m-1 ml-auto custom-button"
                          // onClick={async () => { await refleshTableData(); }}>
                          onClick={handleRefresh}>
                          <span className="btn-text">Actualizar</span>
                          <i
                            className="fas fa-sync-alt me-2"
                            title="Refrescar"
                            style={{ cursor: 'pointer' }}
                            aria-hidden="true"
                          />
                        </button>
                        {/* Alerts modal (uncontrolled) */}
                        <AlertsCreator
                          projects={selectedProjects}
                          devices={deviceOptions}
                          indicators={tableData.length > 0 ? Object.keys(tableData[0]) : []}
                        />



                        {/* <Otro /> */}
                      </div>
                    </>

                  )}


                </div>
                {selectedProjects.length > 0 && tableData.length > 0 && showChart && (
                  <>
                    <div className="row">
                      <ChartComponent datos={chartData} />
                    </div>
                  </>
                )}
                {selectedProjects.length > 0 && tableData.length > 0 && showAlerts && (
                  <>
                    <div className="row">
                      <AlertsList projects={selectedProjects} devices={selectedDevices} />
                    </div>
                  </>
                )}
                <div className="row">
                  {/* Selección de ordenación */}
                  {/* <div className="mb-3">
                    <label htmlFor="sortOrder" className="form-label"><small></small> Ordenar por fecha:</label>

                    <select
                      id="sortOrder"
                      className="form-select"
                      value={sortOrder}
                      onChange={() => console.log(handleSortChange)}
                    >
                      <option value="asc">Fecha Ascendente</option>
                      <option value="desc">Fecha Descendente</option>
                    </select>

                  </div> */}

                </div>
                <div className="row d-flex justify-content-around my-4">
                  {selectedProjects.length > 0 && tableData.length > 0 ? (
                    <div style={{ overflowX: 'auto', fontSize: '0.75rem' }}>
                      <BasicDataTableGraphic order={sortOrder} tableTitle={"Datos"} tableData={tableData} tablePrimaryKey={"id_dato_concatenado"}
                        onDelete={handleDelete}
                      // handleOnClickEdit={() => console.log("handleOnClickEdit")} 
                      // onEdit={() => console.log("handleEdit")} 
                      />
                    </div>
                  ) : (
                    <p>Seleccione proyectos para ver los datos.</p>
                  )}
                </div>

                {selectedProjects.length > 0 && tableData.length > 0 && (
                  <div className="pagination d-flex align-items-center justify-content-center">
                    <button
                      onClick={handleRecentData}
                      disabled={currentPage === 1 || isLoadingSensors}
                      className="btn btn-secondary m-1"
                    >
                      Datos más recientes
                    </button>
                    <span className="m-2">Página {currentPage}</span>
                    <button
                      onClick={handleOlderData}
                      disabled={!hasMore || !nextCursor || isLoadingSensors}
                      className="btn btn-secondary m-1"
                    >
                      Datos anteriores
                    </button>
                    {hasMore && (
                      <span className="text-muted m-2">Hay más datos disponibles</span>
                    )}
                  </div>
                )}
              </div>
            )}
            {!(visitorLoggedIn || username) && (

              <>
                <h2>Acceso Restringido</h2>
                <p>Para ver este contenido, es necesario que inicies sesión.</p>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
};
