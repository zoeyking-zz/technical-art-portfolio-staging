#include"shader.h"

Shader::Shader(const char* vertexPath, const char* fragmentPath)
{
	vertexShaderFile.exceptions(std::ifstream::failbit | std::ifstream::badbit);
	fragmentShaderFlle.exceptions(std::ifstream::failbit | std::ifstream::badbit);

	try {
		vertexShaderFile.open(vertexPath);
		fragmentShaderFlle.open(fragmentPath);

		vertexShaderStream << vertexShaderFile.rdbuf();
		fragmentShaderStream << fragmentShaderFlle.rdbuf();

		vertexShaderFile.close();
		fragmentShaderFlle.close();

		vertexCode = vertexShaderStream.str();
		fragmentcode = fragmentShaderStream.str();

	}catch (std::ifstream::failure e) {
		std::cout << "FAILED::FILES::TO_READ\n";
		glfwTerminate();
		return;
	}

	vertexShaderData = vertexCode.c_str();
	fragmentshaderData = fragmentcode.c_str();
	 
	this->vertex = glCreateShader(GL_VERTEX_SHADER);
	glShaderSource(vertex, 1, &vertexShaderData, NULL);
	glCompileShader(vertex);

	this->fragment = glCreateShader(GL_FRAGMENT_SHADER);
	glShaderSource(fragment, 1, &fragmentshaderData, NULL);
	glCompileShader(fragment);

	int s;
	char inforlog[1024];
	glGetShaderiv(vertex, GL_COMPILE_STATUS, &s);
	if (!s) {
		glGetShaderInfoLog(vertex, 1024, NULL, inforlog);
		std::cout << "Failed::Vertex::" << inforlog << std::endl;
	}
	glGetShaderiv(fragment, GL_COMPILE_STATUS, &s);
	if (!s) {
		glGetShaderInfoLog(fragment, 1024, NULL, inforlog);
		std::cout << "Failed::Fragment::" << inforlog << std::endl;
	}

	this->ID = glCreateProgram();
	glAttachShader(ID, vertex);
	glAttachShader(ID, fragment);

	glLinkProgram(ID);
	glGetProgramiv(ID, GL_LINK_STATUS, &s);
	if (!s) {
		glGetShaderInfoLog(ID, 1024, NULL, inforlog);
		std::cout << "Failed::Program::" << inforlog << std::endl;
	}

	glDeleteShader(vertex);
	glDeleteShader(fragment);
}

Shader::~Shader()
{
}

void Shader::use() {
	glUseProgram(this->ID);
}
void Shader::setFloat(const std::string&name, float value) const {
	glUniform1f(glGetUniformLocation(this->ID, name.c_str()), value);
}
void Shader::setInt(const std::string&name, int value) const {
	glUniform1i(glGetUniformLocation(this->ID, name.c_str()), value);
}
void Shader::setVec3(const std::string&name, float x, float y, float z) {
	glUniform3f(glGetUniformLocation(this->ID, name.c_str()), x, y, z);
}
void Shader::setVec3(const std::string&name, const glm::vec3 &value) {
	glUniform3fv(glGetUniformLocation(this->ID, name.c_str()), 1, glm::value_ptr(value));
}
void Shader::setMat4(const std::string&name, const glm::mat4 &value) {
	glUniformMatrix4fv(glGetUniformLocation(this->ID, name.c_str()), 1, GL_FALSE, glm::value_ptr(value));
}