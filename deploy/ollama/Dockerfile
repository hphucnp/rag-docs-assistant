FROM ollama/ollama:0.18.3-rc1

# Create an entrypoint that ensures model before starting ollama server
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
