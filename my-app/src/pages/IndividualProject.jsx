import { useState, useEffect } from "react";


function IndividualProject() {


    const [project, setProject] = useState(null);



    useEffect(() => {

        fetch("http://127.0.0.1:5000/project_name")

            .then(response => response.json())

            .then(data => {

                setProject(data);

            });


    }, []);



    function checkoutHardware(name){

        console.log(
            "Checkout:",
            name
        );

    }


    function checkinHardware(name){

        console.log(
            "Checkin:",
            name
        );

    }



    if (!project){

        return <h1>Loading...</h1>;

    }



    return (

        <div>


            <h1>
                {project.name}
            </h1>


            <p>
                {project.description}
            </p>



            {
                project.hardware.map((hardware) => (

                    <div key={hardware.name}>


                        <h2>
                            {hardware.name}
                        </h2>


                        <p>
                            Capacity: {hardware.capacity}
                        </p>


                        <p>
                            Available: {hardware.available}
                        </p>


                        <p>
                            Checked out: {hardware.checkedOut}
                        </p>


                        <input
                            type="number"
                            min="0"
                        />


                        <button
                            onClick={() => checkoutHardware(hardware.name)}
                        >
                            Check Out
                        </button>


                        <button
                            onClick={() => checkinHardware(hardware.name)}
                        >
                            Check In
                        </button>


                    </div>

                ))
            }


        </div>

    );


}


export default IndividualProject;