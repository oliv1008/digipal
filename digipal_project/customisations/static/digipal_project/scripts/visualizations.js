// n = 100;
// m = 12;
// v = 2;
// width = 600;
// height = 600;

// let canvas = document.getElementById('canvas');
// let context = canvas.getContext('2d');
// context.lineJoin = "round";
// context.lineCap = "round";
// let animId = 0;
// let tadpoles = new Array(n);

// function init() {
//     if (animId != 0) {
//         window.cancelAnimationFrame(animId);
//     }

//     tadpoles = tadpoles.fill({}).map(() => ({
//         vx: (Math.random() - 0.5) * v,
//         vy: (Math.random() - 0.5) * v,
//         px: new Array(m).fill(Math.random() * width),
//         py: new Array(m).fill(Math.random() * height),
//         count: 0
//     }));

//     animId = window.requestAnimationFrame(draw);
// }

// function draw() {
//     context.clearRect(0, 0, width, height);

//     for (const t of tadpoles) {
//         let dx = t.vx;
//         let dy = t.vy;
//         let x = t.px[0] += dx;
//         let y = t.py[0] += dy;
//         let speed = Math.sqrt(dx * dx + dy * dy);
//         const count = speed * 10;
//         const k1 = -5 - speed / 3;

//         // Bounce off the walls.
//         if (x < 0 || x > width) t.vx *= -1;
//         if (y < 0 || y > height) t.vy *= -1;

//         // Swim!
//         for (var j = 1; j < m; ++j) {
//             const vx = x - t.px[j];
//             const vy = y - t.py[j];
//             const k2 = Math.sin(((t.count += count) + j * 3) / 300) / speed;
//             t.px[j] = (x += dx / speed * k1) - dy * k2;
//             t.py[j] = (y += dy / speed * k1) + dx * k2;
//             speed = Math.sqrt((dx = vx) * dx + (dy = vy) * dy);
//         }
        
//         // Head
//         context.save();
//         context.translate(t.px[0], t.py[0]);
//         context.rotate(Math.atan2(t.vy, t.vx));
//         context.beginPath();
//         context.ellipse(0, 0, 6.5, 4, 0, 0, 2 * Math.PI);
//         context.fill();
//         context.restore();
        
//         // Body
//         context.beginPath();
//         context.moveTo(t.px[0], t.py[0]);
//         for (let i = 1; i < 3; ++i) context.lineTo(t.px[i], t.py[i]);
//         context.lineWidth = 4;
//         context.stroke();
        
//         // Tail
//         context.beginPath();
//         context.moveTo(t.px[0], t.py[0]);
//         for (let i = 1; i < m; ++i) context.lineTo(t.px[i], t.py[i]);
//         context.lineWidth = 2;
//         context.stroke();
//     }

//     animId = window.requestAnimationFrame(draw);
// }

let textsSelected = [];
let annotationSelected = undefined;

function onTextSelected(button) {
    if (button.classList.contains("active")) {
        button.classList.remove("active");
        let index = textsSelected.indexOf(button.dataset.title);
        textsSelected.splice(index, 1);
    }
    else {
        button.classList.add("active");
        textsSelected.push(button.dataset.title.trim());
    }

    extractData();
}

function onAnnotationSelected(button) {
    let activeButtonElt = document.querySelector("button[data-type=annotation].active");
    if (activeButtonElt) {
        activeButtonElt.classList.remove("active");
    }

    button.classList.add("active");
    annotationSelected = button.dataset.code;
    extractData();
}

function extractData() {
    let data = new Map;

    if (textsSelected.length > 0 && annotationSelected) {
        switch (annotationSelected) {
            case "PROS-EV-PSY":
                // We're iterating through every annotations_codes,
                characteristics_as_json.forEach(characteristics => {
                    for (const [keyCode, valueCode] of Object.entries(characteristics['codes'])) {
                        // When we reach the annotations regarding the psychological status
                        if (keyCode.includes("PROS-EV-PSY")) {
                            for (const [keyAnnotation, valueAnnotation] of Object.entries(valueCode['annotations'])) {
                                // In one the previously selected texts
                                if (textsSelected.includes(keyAnnotation.trim())) {
                                    // We add every annotations and its position in that text to an array of shape (annotation_code, position)
                                    let dataAnnotation = [];
                                    valueAnnotation.forEach(valueAnnotationElement => {
                                        dataAnnotation.push([keyCode, valueAnnotationElement['position_percentage']]) 
                                    }); 
                                    // We then add this array to the data dictionnary
                                    // If an entry already exist, it's updated, if not, it's created. 
                                    if (data.get(keyAnnotation)) {
                                        data.set(keyAnnotation, data.get(keyAnnotation).concat(dataAnnotation));
                                    }
                                    else {
                                        data.set(keyAnnotation, dataAnnotation);
                                    }
                                    
                                }
                            }
                        }
                    }
                });
                // We then sort the annotations in ascending order of their appearance for each text
                data.forEach((value, key, map) => value.sort((a,b) => a[1] - b[1]));

                // In the end, the dictionnary looks like this :
                // {
                //     "text1" : [[annotation_code, position], ..., [annotation_code, position]],
                //     ...,
                //     "text5" : [[annotation_code, position], ..., [annotation_code, position]]
                // }

                break;
        }
    }

    drawResult(data);
}

function drawResult(data) {
    console.log(data);
    d3.select("#graph").selectChildren().remove();
    if (data.size > 0) {
        switch(annotationSelected) {
            case "PROS-EV-PSY":
                drawPsychologicalGraph(data);
                break;
        }
    }
}

function drawPsychologicalGraph(data) {
    let width = 800;
    let height = 400;
    let margin = ({top: 20, right: 30, bottom: 30, left: 100});
    strokeLinecap = "round"; // stroke line cap of the line
    strokeLinejoin = "round"; // stroke line join of the line
    strokeWidth = 1.5; // stroke width of line, in pixels
    strokeOpacity = 1; // stroke opacity of line

    // Construct scales and axes.
    // The X-Axis is linear and quantitative : from the beginning of the text (0%) to its end (100%)
    const xScale = d3.scaleLinear()
        .domain([0, 100])
        .range([margin.left, width - margin.right])
        .interpolate(d3.interpolateRound)
    // The Y-Axis is qualitative : either #PROS-EV-PSY-BON of #PROS-EV-PSY-MAL 
    const yScale = d3.scalePoint()
        .domain(["#PROS-EV-PSY-BON", "#PROS-EV-PSY-MAL"])
        .range([margin.top, height - margin.bottom])
        .padding(0.1)
        .round(true)

    const xAxis = d3.axisBottom(xScale);
    const yAxis = d3.axisLeft(yScale);

    // The main svg node
    const svg = d3.create("svg")
                  .attr("width", width)
                  .attr("height", height)
                  .attr("viewBox", [0, 0, width, height])
                  .attr("style", "max-width: 100%; height: auto; height: intrinsic;");
    // The X-axis
    svg.append("g")
        .attr("transform", `translate(0, ${height - margin.bottom})`)
        .call(xAxis)
        .call(g => g.append("text")
            .attr("x", 350)
            .attr("y", margin.bottom)
            .attr("fill", "currentColor")
            .attr("text-anchor", "start")
            .attr("font-weight", "bold")
            .text("Position en pourcentage dans le texte"));
    // The Y-Axis
    svg.append("g")
       .attr("transform", `translate(${margin.left},0)`)
       .call(yAxis)
       .call(g => g.select(".domain").remove())

    // We draw each lines and set of points/annotations individually 
    let iter = 8;
    data.forEach( (value, key, map) => {
        color = d3.schemeSet1[iter]; // stroke color of line
        if (iter > 0) {
            iter = iter - 1;
        }
        
        // Compute values.
        const X = d3.map(value, d => d[1]);
        const Y = d3.map(value, d => d[0]);
        const I = d3.range(X.length);

        // Construct a line generator.
        const line = d3.line()
            .curve(d3.curveLinear)
            .x(d => xScale(X[d]))
            .y(d => yScale(Y[d]));

        // The line connecting the dots 
        svg.append("path")
            .attr("fill", "none")
            .attr("stroke", color)
            .attr("stroke-width", strokeWidth)
            .attr("stroke-linecap", strokeLinecap)
            .attr("stroke-linejoin", strokeLinejoin)
            .attr("stroke-opacity", strokeOpacity)
            .attr("d", line(I));
        // The dots corresponding to the annotations in the text
        svg.append("g")
                .attr("stroke", "#000")
                .attr("stroke-opacity", 0.2)
            .selectAll("circle")
            .data(value)
            .join("circle")
                .attr("cx", d => xScale(d[1])) // We set the position thanks the scale which give us the absolute value.
                .attr("cy", d => yScale(d[0]))
                .attr("fill", d => (d[0] === "#PROS-EV-PSY-BON") ? "blue" : "red")
                .attr("r", 5);

    }) 
        
    d3.select("#graph").node().append(svg.node());
}