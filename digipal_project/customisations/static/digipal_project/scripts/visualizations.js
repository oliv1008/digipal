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

let textSelected = undefined;
let annotationSelected = undefined;

function onTextSelected(button) {
    let activeButtonElt = document.querySelector("button[data-type=text].active");
    if (activeButtonElt) {
        activeButtonElt.classList.remove("active");
    }

    button.classList.add("active");
    textSelected = button.dataset.title;
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
    let data = [];

    if (textSelected && annotationSelected) {
        switch (annotationSelected) {
            case "PROS-EV-PSY":
                // We're iterating through every annotations_codes,
                characteristics_as_json.forEach(characteristics => {
                    for (const [keyCode, valueCode] of Object.entries(characteristics['codes'])) {
                        // When we reach the annotations regarding the psychological status
                        if (keyCode.includes("PROS-EV-PSY")) {
                            for (const [keyAnnotation, valueAnnotation] of Object.entries(valueCode['annotations'])) {
                                // In the previously selected text
                                if (keyAnnotation.trim() === textSelected.trim()) {
                                    valueAnnotation.forEach(valueAnnotationElement => {
                                        // We add every annotations and its position in that text to an array of shape [[annotation_code, position]]
                                        data.push([keyCode, valueAnnotationElement['position_percentage']]) 
                                    }); 
                                }
                            }
                        }
                    }
                });
                // We then sort the annotations in ascending order of their appearance in the text
                data.sort((a, b) => a[1] - b[1]);
                break;
        }
    }

    if (data.length > 0) {
        drawResult(data);
    }
}

function drawResult(data) {
    d3.select("#graph").selectChildren().remove();
    d3.select("#graph").node().append(drawPsychologicalGraph(data));
}

function drawPsychologicalGraph(data) {
    let width = 800;
    let height = 400;
    let margin = ({top: 20, right: 30, bottom: 30, left: 100});
    color = "steelblue"; // stroke color of line
    strokeLinecap = "round"; // stroke line cap of the line
    strokeLinejoin = "round"; // stroke line join of the line
    strokeWidth = 1.5; // stroke width of line, in pixels
    strokeOpacity = 1; // stroke opacity of line

    // Compute values.
    const X = d3.map(data, d => d[1]);
    const Y = d3.map(data, d => d[0]);
    const I = d3.range(X.length);

    // Construct scales and axes.
    const xScale = d3.scaleLinear()
        .domain([0, 100])
        .range([margin.left, width - margin.right])
        .interpolate(d3.interpolateRound)

    const yScale = d3.scalePoint()
        .domain(["#PROS-EV-PSY-BON", "#PROS-EV-PSY-MAL"])
        .range([margin.top, height - margin.bottom])
        .padding(0.1)
        .round(true)

    const xAxis = d3.axisBottom(xScale);
    const yAxis = d3.axisLeft(yScale);

    // Construct a line generator.
    const line = d3.line()
                   .curve(d3.curveLinear)
                   .x(d => xScale(X[d]))
                   .y(d => yScale(Y[d]));

    const svg = d3.create("svg")
                  .attr("width", width)
                  .attr("height", height)
                  .attr("viewBox", [0, 0, width, height])
                  .attr("style", "max-width: 100%; height: auto; height: intrinsic;");

    svg.append("g")
        .attr("transform", `translate(0, ${height - margin.bottom})`)
        .call(xAxis)

    svg.append("g")
       .attr("transform", `translate(${margin.left},0)`)
       .call(yAxis)
       .call(g => g.select(".domain").remove())

    svg.append("path")
       .attr("fill", "none")
       .attr("stroke", color)
       .attr("stroke-width", strokeWidth)
       .attr("stroke-linecap", strokeLinecap)
       .attr("stroke-linejoin", strokeLinejoin)
       .attr("stroke-opacity", strokeOpacity)
       .attr("d", line(I));

    svg.append("g")
            .attr("stroke", "#000")
            .attr("stroke-opacity", 0.2)
        .selectAll("circle")
        .data(data)
        .join("circle")
            .attr("cx", d => xScale(d[1]))
            .attr("cy", d => yScale(d[0]))
            .attr("fill", d => (d[0] === "#PROS-EV-PSY-BON") ? "blue" : "red")
            .attr("r", 5);

    return svg.node();
}