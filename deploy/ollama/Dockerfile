FROM ollama/ollama:0.18.3-rc1

# Copy the model ensure script
COPY scripts/ensure-embedding-model.sh /tmp/ensure-embedding-model.sh
RUN chmod +x /tmp/ensure-embedding-model.sh

# Create an entrypoint that ensures model before starting ollama server
COPY deploy/ollama/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
