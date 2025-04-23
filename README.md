# GCPCloudRunFunctionsC2Forwarder

This Google Cloud Run Function application can be used to forward traffic fronted from the Google Cloud Run domain to a C2 server running on a GCP compute instance VM.

This is a POC application only and has a few potential indicators that could be use to identify running instances, so read the code in main.py and modify as required before attempting to use.


# Pre deployment setup and configuration

Setup a project in GCP with a VPC (the default one is fine) and at least one compute instance running a C2 server with a HTTP listener. In more complex setups you can use a multi host setup with a HTTP proxy (Apache, Nginx, etc) that filters and then forwards HTTP traffic to the C2s HTTP listener on another host to provide some seperation and protection for the C2 server. Take note of the IP address of the C2 server (or proxy server in a multi host setup), as we will need to specify this at deploy time for the application.

Depending on the deployment approach, you may need to setup a Serverless VPC connector in your VPC with an unused IP address range in the same region as your Cloud Run Function and VM instance. This is done in the console [here](https://console.cloud.google.com/networking/connectors/list). This is required to allow traffic from the function to the private IP address of your C2 instance - so you dont need to directly expose the HTTP interface of the C2/proxy to the Internet. Take note of the name of the connector as we need it when we configure the app before deployment - I called mine `testconnector`.

Setup a firewall rule for the VPC which allows traffic from the VPC connectors private IP address range to the HTTP endpoint listeners port on the destination C2 host (or proxy in the multi host configuration).

In my test environment, I chose to deploy the container to the same subnet as the destination compute VM (which was the default subnet in the same region), and created a [firewall rule](https://console.cloud.google.com/net-security/firewall-manager/firewall-policies/list) that allowed all internal traffic to port 80 on the destination host from all other hosts in the subnet. You can choose a more segmented approach if you wish.


# Deployment variables


The example deployment steps below will reference some of the following variables you will want to replace with your own appropriate values when deploying the app, taking the pre deployment steps as discussed above into consideration:
* `<SERVICE_NAME>` - the name for the cloud run service you will deploy - can be almost any arbitrary string, but will appear in the auto-generated domain so dont be too obvious about it if you want deniability
* `<REGION>` - the GCP region in which the Cloud Run app will be deployed e.g. `us-central1`
* `<C2_INTERNAL_IP>` - the internal IP address of the C2 HTTP listener you want to forward traffic to
* `<PROJECT_ID>` - ID of the GCP project in which you are deploying resources, can be obtained from various locations in the console such as the [welcome page](https://console.cloud.google.com/welcome/new)
* `<CONNECTOR_NAME>` - name of the Serverless VPC connector you setup as described above, e.g. `testconnector`
* `<SUBNET_NAME>` - name of the subnet to which you want your Cloud Run container to be connected to, e.g. `default`


# Deployment steps


[Install and configure](https://cloud.google.com/sdk/docs/install) the GCloud CLI. 


Configure the CLI for your project

```
gcloud config set project <PROJECT_ID>
```

Enable the appropriate APIs in GCP:

```
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

Deploy the application, using this repository as the present working directory

There are two different ways to approach deployment, which each have their own benefits and drawbacks. 
1. The `gcloud functions` approach which deploys your app so its accessible from three different auto created URLs instad of only two, but requires a Serverless VPC connector (with associated running cost) to allow private VPC connection to a C2 running on a GCP compute instance
2. The `gcloud run` approach which does not require the Serverless VPC connector, but only provides access to the app via two auto created URLs, excluding the `cloudfunctions.net` domain URL available when using the first approach


## Gcloud functions deployment approach

This approach requires the Serverless VPC connector to work but gives access to an additional endpoint where the app can be accessed.

```
gcloud functions deploy <SERVICE_NAME> --source . --entry-point main --region <REGION> --runtime python312 --set-env-vars='DESTINATION=<C2_INTERNAL_IP>' --trigger-http --allow-unauthenticated --vpc-connector 'projects/<PROJECT_ID>/locations/<REGION>/connectors/<CONNECTOR_NAME>'

```

Once complete this will spit out a URL at which your C2 service can be reached, with a form similar to the following: `https://<REGION>-<PROJECT_ID>.cloudfunctions.net/<SERVICE_NAME>`. Two additional alternate URLs from which the app can also be reached will also be auto configured, discussed below and viewable from the Network tab of the [GCP Cloud Run console](https://console.cloud.google.com/run).


## Gcloud run deployment approach

This approach does not require the Serverless VPC connector and instead uses the [Direct VPC egress](https://cloud.google.com/run/docs/configuring/vpc-direct-vpc) to run the app inside an existing VPC subnet. This saves you some money and complexity but you lose acess to the `cloudfunctions.net` address for the app, and instead only have acces to the two alternate address forms.

```
gcloud run deploy <SERVICE_NAME> --source . --function main --set-env-vars='DESTINATION=<C2_INTERNAL_IP>' --region=<REGION> --allow-unauthenticated --subnet='projects/<PROJECT_ID>/regions/<REGION>/subnetworks/<SUBNET_NAME>' 
```

The `--subnet` switch value above refers to the internal resource name of the subnet to which you want to attach your Cloud Run container, you should confirm it is referring to the correct resource using the [GCP subnets page](https://console.cloud.google.com/networking/networks/list?pageTab=CURRENT_PROJECT_SUBNETS) if you have any issues.


Once complete this will spit out a URL at which your C2 service can be reached, with a form similar to the following: `https://<SERVICE_NAME>-<12_DIGIT_NUMBER>.<REGION>.run.app/`. This form of URL will also be available when using the `gcloud functions` deployment approach.

Both approaches will also have access to the app at a shorter form version of the URL in a format similar to the following: `https://<SERVICE_NAME>-<10_CHAR_STRING>-<REGION-ID>.a.run.app/`


You can monitor/troubleshoot/delete the application after this point using the [GCP Cloud Run console](https://console.cloud.google.com/run), where all of the available URLs for your app will also be viewable in the Network tab.