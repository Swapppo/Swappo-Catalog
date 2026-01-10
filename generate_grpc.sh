#!/bin/bash
# Generate Python gRPC code from proto files

python -m grpc_tools.protoc \
  -I./protos \
  --python_out=. \
  --grpc_python_out=. \
  ./protos/catalog.proto

echo "✅ Generated catalog_pb2.py and catalog_pb2_grpc.py"
