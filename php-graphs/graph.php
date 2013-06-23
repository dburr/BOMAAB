<?php

// change to where you have installed the JpGraph library
require_once('jpgraph/src/jpgraph.php');
require_once('jpgraph/src/jpgraph_line.php');

// change base_url to where you have the BOMAAB php-script
// installed
$base_url = "http://beta.DonaldBurr.com/BOMAAB/index.php";

// end of user-configurable values

// determine what type of graph to do
$do_iap_graph = $_GET['type'] === "iap" ? true : false;

// set up the graph
// Width and height of the graph
$width = 800; $height = 400;
// Create a graph instance
$graph = new Graph($width,$height);
// Specify what scale we want to use,
// text = textual label scale for the X-axis
// int = integer scale for the Y-axis
$graph->SetScale('textint');
// Setup X-axis titles and labels
$graph->xaxis->title->Set('DATE');
$graph->xaxis->SetLabelAngle(45);
$graph->xaxis->SetTextLabelInterval(2);
// Setup Y-axis title
$graph->yaxis->title->Set('SALES');
 
$json = file_get_contents($base_url . ($do_iap_graph ? "?iap" : ""));
$data = json_decode($json, true);

$set_up_tick_labels = false;
$dates = array();

// set the graph title
$graph_title = $data['graph']['title'];
$graph->title->Set($graph_title);

// iterate through all date sequences
$data_sequences = $data['graph']['datasequences'];
foreach ($data_sequences as $ds) {
  $vals = array();
  $ds_name = $ds['title'];
  $ds_points = $ds['datapoints'];
  foreach ($ds_points as $dp) {
    $dp_title = $dp['title'];
    $dp_value = $dp['value'];

    // only need to do this once
    if (!$set_up_tick_labels)  {
      $dates[] = $dp_title;
    }

    // add to values
    $vals[] = $dp_value;
  }

  // only need to do this once
  if (!$set_up_tick_labels)  {
    $graph->xaxis->SetTickLabels($dates);
    //$graph->SetScale('intint',0,0,0,count($dates)-1);
    $set_up_tick_labels = true;
  }

  // Create the linear plots
  $lineplot=new LinePlot($vals);
  $lineplot->SetLineWeight(20); 
  $lineplot->SetLegend($ds_name);
  // Add the plot to the graph
  $graph->Add($lineplot);
}

// Display the graph
$graph->Stroke();
?>
