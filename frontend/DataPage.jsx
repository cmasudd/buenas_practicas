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

// 2025-06-23T21:33:25



export const DataPage = () => {
  // login
  const { accounts } = useMsal();
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
  const [totalPages, setTotalPages] = useState(0);
  const rowsPerPage = 25; // Número máximo de filas por página
  const [sortOrder, setSortOrder] = useState("desc")

  // Hooks para obtener datos de las tablas
  const { data: projectsData, isLoading: isLoadingProjects } = useFetch(`${import.meta.env.VITE_API_URL}/listarDatos?tabla=${projectsTableName}`);
  const { data: devicesData, setUrl: devicesSetUrl, isLoading: isLoadingDevices } = useFetch('');
  const { data: sensorsData, setUrl: sensorsSetUrl, isLoading: isLoadingSensors } = useFetch('');

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
    refleshTableData();
    const desc = projectsData?.data?.tableData?.filter(proj => proj?.id_proyecto === selectedProjects[0]?.value);
    const handleSetDesc = () => {
      if (desc && desc.length > 0) {
        setDescripcion(desc[0]?.descripcion || "");
      }
    }
    handleSetDesc();
    // console.log(projectsData.data.tableData);
    // console.log(selectedProjects[0]?.value);

  }, [selectedProjects, selectedDevices, startDate, endDate, currentPage, refreshCount]);
  const handleRefresh = () => {
    setRefreshCount(c => c + 1);
  };
  // Actualiza la peticion de datos dependiendo de dispositivos y proyectos seleccionados
  const refleshTableData = async () => {
    console.log("actualizando datos")
    if (selectedProjects.length > 0) {
      const projectIds = selectedProjects.map((project) => project.value).join(',');
      const deviceIds = selectedDevices.map((device) => device.label).join(',');
      console.log('refleshTableData filters:', { projectIds, deviceIds, startDate, endDate, currentPage, refreshCount });
      setIsLoading(true);
      devicesSetUrl(`${import.meta.env.VITE_API_URL}/listarDatos?tabla=${devicesTableName}&id_proyecto=${projectIds}`);

      // parámetro único para forzar el fetch
      const refreshParam = `refresh=${Date.now()}`;
      // let url = `${import.meta.env.VITE_API_URL}/listarDatosEstructuradosV2?tabla=datos&disp.id_proyecto=${projectIds}&limite=${rowsPerPage}&offset=${(currentPage - 1) * rowsPerPage}&${refreshParam}`;
      let url = `${import.meta.env.VITE_API_URL}/listarDatosEstructuradosV2?tabla=datos&order_by=fecha_insercion&disp.id_proyecto=${projectIds}&limite=${rowsPerPage}&offset=${(currentPage - 1) * rowsPerPage}`;

      if (selectedDevices.length > 0) {
        url += `&disp.codigo_interno=${deviceIds}`;
        if (startDate) url += `&fecha_inicio=${startDate}`;
        if (endDate) url += `&fecha_fin=${endDate}`;

        console.log('refleshTableData url:', url);

        sensorsSetUrl(url);
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
      let totalCount = sensorsData.data.totalCount || 0;
      setTotalPages(Math.ceil(totalCount / rowsPerPage));
    } else {
      setTableData([]);
      setTotalPages(0);
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
  };

  const handleDeviceChange = (selectedDevices) => {
    console.log('selectedDevices', selectedDevices);
    setSelectedDevices(selectedDevices || []); // Permite deseleccionar todo
    setCurrentPage(1);
  };

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const handleStartDateChange = (event) => {
    setStartDate(event.target.value);
    setCurrentPage(1); // Resetear a la primera página
  };

  const handleEndDateChange = (event) => {
    setEndDate(event.target.value);
    setCurrentPage(1); // Resetear a la primera página
  };

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
                        <button className="btn m-1 ml-auto custom-button" onClick={downloadFile}>
                          <span className="btn-text">Descargar CSV</span>
                          <i className="fas fa-plus-circle"></i>
                        </button>
                        <button className="btn m-1 ml-auto custom-button" onClick={downloadExcel}>
                          <span className="btn-text">Descargar Excel</span>
                          <i className="fas fa-plus-circle"></i>
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

                {selectedProjects.length > 0 && tableData.length > 0 && (<div className="pagination">
                  {Array.from({ length: totalPages }, (_, index) => {
                    const pageNumber = index + 1;

                    // Siempre muestra la primera página
                    if (pageNumber === 1) {
                      return (
                        <button
                          key={index}
                          onClick={() => handlePageChange(pageNumber)}
                          className={`btn ${currentPage === pageNumber ? 'btn-dark' : 'btn-secondary'} m-1`}
                        >
                          {pageNumber}
                        </button>
                      );
                    }

                    // Siempre muestra la última página
                    if (pageNumber === totalPages) {
                      return (
                        <button
                          key={index}
                          onClick={() => handlePageChange(pageNumber)}
                          className={`btn ${currentPage === pageNumber ? 'btn-dark' : 'btn-secondary'} m-1`}
                        >
                          {pageNumber}
                        </button>
                      );
                    }

                    if (
                      (pageNumber >= currentPage - 4 && // Desde 4 páginas antes de la actual
                        pageNumber <= currentPage + 4) ||
                      (currentPage < 7 && pageNumber < 10)
                    ) {
                      return (
                        <button
                          key={index}
                          onClick={() => handlePageChange(pageNumber)}
                          className={`btn ${currentPage === pageNumber ? 'btn-dark' : 'btn-secondary'} m-1`}
                        >
                          {pageNumber}
                        </button>
                      );
                    }

                    // Mostrar puntos suspensivos cuando haya saltos entre páginas
                    if (
                      (pageNumber === 2 && currentPage > 6) ||
                      (pageNumber === totalPages - 1 && currentPage < totalPages - 5)
                    ) {
                      return (
                        <span key={index} className="btn disabled m-1">
                          ...
                        </span>
                      );
                    }
                    return null;
                  })}
                </div>)}
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
