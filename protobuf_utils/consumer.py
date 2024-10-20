from kafka import KafkaConsumer
import json
import argparse
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory, json_format
import os
import time

def load_message_descriptor(fd_path, msg_name):
    # Read the file descriptor
    if not os.path.exists(fd_path):
        raise FileNotFoundError(f"File not found: {fd_path}")
    
    with open(fd_path, 'rb') as f:
        file_content = f.read()

    # Unmarshal the file descriptor set
    file_set = descriptor_pb2.FileDescriptorSet()
    file_set.ParseFromString(file_content)

    # Create a descriptor pool and add the file descriptors
    pool = descriptor_pool.DescriptorPool()
    for fd_proto in file_set.file:
        pool.Add(fd_proto)

    # Find the message descriptor
    try:
        message_descriptor = pool.FindMessageTypeByName(msg_name)
        return message_descriptor
    except KeyError:
        raise ValueError(f"Unable to find message named {msg_name} in file descriptor")

def protobuf_consume(brokers, descriptor, name, topic):
    # Load the message descriptor
    message_descriptor = load_message_descriptor(descriptor, name)

    # Create a Kafka consumer
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=brokers,
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        value_deserializer=lambda x: x
    )

    # Create a message factory
    factory = message_factory.MessageFactory()
    message_class = factory.GetPrototype(message_descriptor)

    print(f"Consuming messages from topic {topic}...")
    while True:
        try:
            # Poll for messages with a timeout
            message_pack = consumer.poll(timeout_ms=1000)
            if not message_pack:
                continue

            for tp, messages in message_pack.items():
                for message in messages:
                    # Deserialize the Protobuf message
                    dymsg = message_class()
                    dymsg.ParseFromString(message.value)

                    # Convert the Protobuf message to JSON
                    json_message = json_format.MessageToJson(dymsg)
                    print(json_message)
        except KeyboardInterrupt:
            print("Interrupted by user, shutting down...")
            break