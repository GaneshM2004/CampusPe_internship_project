# Use official Java 17 image (change to 21 if you used Java 21)
FROM eclipse-temurin:17-jdk-alpine

# Set working directory
WORKDIR /app

# Copy the Maven wrapper and project files
COPY mvnw .
COPY .mvn .mvn
COPY pom.xml .
COPY src src

# Build the application (skips tests for faster build)
RUN ./mvnw clean package -DskipTests

# Copy the built jar to a simpler name
RUN cp target/*.jar app.jar

# Expose port 8080
EXPOSE 8080

# Run the Java application
ENTRYPOINT ["java","-jar","app.jar"]