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
let data = new Map;

function onTextSelected(button) {
    if (button.classList.contains("active")) {
        button.classList.remove("active");
        let index = textsSelected.indexOf(button.dataset.title.trim());
        textsSelected.splice(index, 1);
        data.delete(button.dataset.title.trim());
    }
    else {
        button.classList.add("active");
        textsSelected.push(button.dataset.title.trim());
    }

    constructData();
}

function onAnnotationSelected(button) {
    let activeButtonElt = document.querySelector("button[data-type=annotation].active");
    if (activeButtonElt) {
        activeButtonElt.classList.remove("active");
    }

    button.classList.add("active");
    annotationSelected = button.dataset.code;
    data = new Map;
    constructData();
}

// Construct the data dictionnary to be visualized from the characteristics dictionnary 
function constructData() {
    if (textsSelected.length > 0 && annotationSelected) {
        switch (annotationSelected) {
            case "PROS-EV-PSY":
                // For each selected texts
                textsSelected.forEach( text => {
                    // If the data does not already contains the text informations 
                    if (!data.has(text)) {
                        let dataAnnotation = [];
                        // We're iterating through all of the annotations code for that characteristic 
                        for (const [keyCode, valueCode] of Object.entries(characteristics_as_json[3]["codes"])) {
                            // If the text contains annotations regarding that characteristic
                            if (valueCode["annotations"][text] != undefined) {
                                // We're adding them and their position
                                valueCode["annotations"][text].forEach( value => {
                                    dataAnnotation.push(new Map([["annotation_code", keyCode], 
                                                                ["position", value["position_percentage"]], 
                                                                ["content", value["content"]], 
                                                                ["url", value["url"]]]))
                                })
                            }
                        }
                        // We then sort the annotations in ascending order of their appearance for each text
                        dataAnnotation.sort((a,b) => a.get("position") - b.get("position"));

                        data.set(text, dataAnnotation);
                    }
                });

                // In the end, the dictionnary looks like this :
                // {
                //     "text1" : [{annotation_code, position, content, url}, ..., {annotation_code, position, content, url}],
                //     ...,
                //     "text5" : [{annotation_code, position, content, url}, ..., {annotation_code, position, content, url}]
                // }

                break;
        }
    }

    drawResult();
}

function drawResult() {
    console.log(textsSelected);
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

// Show the tooltip containing the sentence annoted
function mouseEntered(event) {
    // We retrieve the arguments passed with the ".bind()" method
    const data = this.data
    const xScale = this.xScale;
    const yScale = this.yScale;
    const tooltip = this.tooltip;

    // We retrieve the value of the annotation which fired the event from the data dictionnary
    // (We could have passed as an argument the value of the annotation directly from line/dots drawing loop but the tooltip would have been drawn over by the next line)
    let content;
    let index;
    let keyIndex;
    let position;
    let annotation_code;
    for (const [key, value] of data) {
        index = value.findIndex( (element) => element === event.currentTarget.__data__);
        if (index != -1) {
            keyIndex = key;
            content = value[index].get("content");
            position = value[index].get("position");
            annotation_code = value[index].get("annotation_code");
            break;
        }
    }

    tooltip.style("display", null);
    tooltip.attr("transform", `translate(${xScale(position)},${yScale(annotation_code) -  50})`);

    // The tooltip panel
    const path = tooltip.selectAll("path")
    .data([,])
    .join("path")
        .attr("fill", "white")
        .attr("stroke", "black");

    // The tooltip content
    const text = tooltip.selectAll("text")
    .data([,])
    .join("text")
    .call(text => text
        .selectAll("tspan")
        .data(content.split(/\n/))
        .join("tspan")
        .attr("x", 0)
        .text(d => d));

    // We're drawing the text and the panel (l-5,5 l-5,-5 is for the arrow) and centering them
    const {x, y, width: w, height: h} = text.node().getBBox();
    const margin = ({top : 10, right : 10, bottom : 10, left : 10});
    text.attr("transform", `translate(${-w / 2}, ${27})`);
    path.attr("d", `M${-w / 2 - margin.left}, ${margin.top}
                    h${w + margin.left + margin.right}
                    v${h + margin.bottom}
                    h${-w / 2 - margin.right + 5}
                    l-5,5
                    l-5,-5
                    h${-w / 2 - margin.left + 5}
                    v${-h - margin.top}`);
}

function mouseLeft(event) {
    const tooltip = this.tooltip;
    const svg = this.svg;
    
    tooltip.style("display", "none");
    svg.node().value = null;
}

// Open a new tab with the annotation highlighted in its text
function click(event) {
    // We retrieve the value of the annotation which fired the event from the data dictionnary
    // (We could have passed as an argument the value of the annotation directly from line/dots drawing loop but the tooltip would have been drawn over by the next line)
    let url;
    let index;
    for (const [key, value] of data) {
        index = value.findIndex( (element) => element === event.currentTarget.__data__);
        if (index != -1) {
            url = value[index].get("url");
            break;
        }
    }
    // I could have used window.open() but it open a new tab or a new window depending on the user's browser settings, this always open a new tab
    a = document.createElement("a");
    a.setAttribute("href", url);
    a.setAttribute("target", "_blank"); 
    a.click()
}

function drawPsychologicalGraph(data) {
    let width = 1200;
    let height = 400;
    let margin = ({top: 20, right: 200, bottom: 30, left: 100});
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
                  .attr("style", "max-width: 100%; height: auto;");
    // The X-axis
    svg.append("g")
        .attr("transform", `translate(0, ${height - margin.bottom})`)
        .call(xAxis)
        .call(g => g.append("text")
            .attr("x", 460)
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
    let iter = 0;
    data.forEach( (value, key, map) => {
        color = d3.schemeSet1[8 - iter]; // stroke color of line, starting from the end because I prefer the colors
        if (iter < 7) {
            iter = iter + 1;
        }
        
        // Compute values.
        const X = d3.map(value, d => d.get("position"));
        const Y = d3.map(value, d => d.get("annotation_code"));
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
            .attr("d", line(I))
            .style("pointer-events", "none");

        // The dots corresponding to the annotations in the text
        svg.append("g")
            .attr("stroke", "#000")
            .attr("stroke-opacity", 0.2)
            .selectAll("circle")
            .data(value)
            .join("circle")
                .attr("cx", d => xScale(d.get("position"))) // We set the positions thanks to the scales which give us the absolute values.
                .attr("cy", d => yScale(d.get("annotation_code")))
                .attr("fill", d => (d.get("annotation_code") === "#PROS-EV-PSY-BON") ? "blue" : "red")
                .attr("r", 5)
                .style("cursor", "pointer")

        // The legend
        svg.append("line")
           .attr("fill", "none")
           .attr("stroke", color)
           .attr("stroke-width", strokeWidth)
           .attr("stroke-linecap", strokeLinecap)
           .attr("stroke-linejoin", strokeLinejoin)
           .attr("stroke-opacity", strokeOpacity)
           .attr("x1", 1025)
           .attr("x2", 1075)
           .attr("y1", margin.top + iter * 50)
           .attr("y2", margin.top + iter * 50)

        svg.append("text")
           .attr("x", 1085)
           .attr("y", margin.top + 4 + iter * 50)
           .attr("textLength", 100)
           .text(key.slice(0, 10).concat("..."))
    })

    // The tooltip appearing on mouseover 
    // We draw it last because we want it over every other element (lines and dots)
    const tooltip = svg.append("g")
        .style("pointer-events", "none");
    
    // The use of ".bind()" is one of the only way to pass parameters to an event handler, it replace the result of the "this" keywork with the value of the argument
    svg.selectAll("circle")
       .on("mouseenter", mouseEntered.bind({"data" : data, "xScale" : xScale, "yScale" : yScale, "tooltip" : tooltip}))
       .on("mouseleave", mouseLeft.bind({"tooltip" : tooltip, "svg" : svg}))
       .on("click", click.bind({"data" : data}));
        
    d3.select("#graph").node().append(svg.node());
}