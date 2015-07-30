#! /bin/bash

curl -i -H "Content-Type: application/xml" -H "Accept: application/xml" -X POST -d @inform.xml http://localhost:8000
curl -i -H "Content-Type: application/xml" -H "Accept: application/xml" -X POST -d @empty.xml http://localhost:8000
curl -i -H "Content-Type: application/xml" -H "Accept: application/xml" -X POST -d @gpn_resp-IGD.xml http://localhost:8000
curl -i -H "Content-Type: application/xml" -H "Accept: application/xml" -X POST -d @gpn_resp-IGD-DeviceInfo.xml http://localhost:8000
curl -i -H "Content-Type: application/xml" -H "Accept: application/xml" -X POST -d @gpv_resp-IGD-DeviceInfo.xml http://localhost:8000
curl -i -H "Content-Type: application/xml" -H "Accept: application/xml" -X POST -d @gpn_resp-IGD-ManagementServer.xml http://localhost:8000
curl -i -H "Content-Type: application/xml" -H "Accept: application/xml" -X POST -d @gpv_resp-IGD-ManagementServer.xml http://localhost:8000
curl -i -H "Content-Type: application/xml" -H "Accept: application/xml" -X POST -d @gpn_resp-IGD-DeviceInfo-MemoryStatus.xml http://localhost:8000
curl -i -H "Content-Type: application/xml" -H "Accept: application/xml" -X POST -d @gpv_resp-IGD-DeviceInfo-MemoryStatus.xml http://localhost:8000
