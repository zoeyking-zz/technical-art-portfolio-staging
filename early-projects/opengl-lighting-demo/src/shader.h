#pragma once
#include <GL/glew.h>
#include<GLFW/glfw3.h>

#include<iostream>
#include<fstream>
#include<sstream>
#include<string>

#include "glm/glm.hpp"
#include "glm/gtc/matrix_transform.hpp"
#include "glm/gtc/type_ptr.hpp"

class Shader
{
public:

	GLuint ID;

	Shader(const char* vertexPath,const char* fragmentPath);
	~Shader();

	void use();
	void setFloat(const std::string&name, float value) const;
	void setInt(const std::string&name, int value)const;
	void setVec3(const std::string&name, float x,float y,float z);
	void setVec3(const std::string&name, const glm::vec3 &value);
	void setMat4(const std::string&name, const glm::mat4 &value);

private:
	std::string vertexCode, fragmentcode;
	std::ifstream vertexShaderFile, fragmentShaderFlle;
	const char*vertexShaderData, *fragmentshaderData;
	std::stringstream vertexShaderStream, fragmentShaderStream;
	GLuint vertex, fragment;
};


